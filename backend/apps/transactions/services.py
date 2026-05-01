from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.db.models import Q

from apps.categories.models import Category
from apps.currencies.models import Currency
from apps.currencies.services import UnknownCurrencyError, get_exchange_rate
from common.exceptions import (
    CategoryNotFoundError,
    TransactionNotFoundError,
)

from .models import Transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

QUANTIZE = Decimal("0.00000001")


def _get_accessible_category(*, category_id: int, user: AbstractBaseUser) -> Category:
    try:
        return cast(Category, Category.objects.get(Q(is_system=True) | Q(owner=user), id=category_id))
    except Category.DoesNotExist:
        raise CategoryNotFoundError(
            f"Category {category_id} not found or not accessible."
        ) from None


def _compute_fx(
    *,
    amount: Decimal,
    currency_code: str,
    base_currency: str,
    tx_date: date_type,
    fx_rate_override: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Return (amount_base, fx_rate_snapshot). Short-circuits when currencies match."""
    if currency_code == base_currency:
        return amount, Decimal("1")
    if fx_rate_override is not None:
        rate = fx_rate_override.quantize(QUANTIZE)
    else:
        rate = get_exchange_rate(currency_code, base_currency, at=tx_date).quantize(QUANTIZE)
    return (amount * rate).quantize(QUANTIZE), rate


def create_transaction(
    *,
    user: AbstractBaseUser,
    account: Any,
    type: str,
    amount: Decimal,
    currency_code: str,
    category_id: int | None,
    date: date_type,
    description: str = "",
    reference: str = "",
    fx_rate_override: Decimal | None = None,
) -> Transaction:
    if not Currency.objects.filter(code=currency_code).exists():
        raise UnknownCurrencyError(f"Unknown currency: {currency_code}")

    category = None
    if category_id is not None:
        category = _get_accessible_category(category_id=category_id, user=user)

    base_currency: str = user.default_currency_code  # type: ignore[attr-defined]
    amount_base, fx_rate_snapshot = _compute_fx(
        amount=amount,
        currency_code=currency_code,
        base_currency=base_currency,
        tx_date=date,
        fx_rate_override=fx_rate_override,
    )

    return cast(
        Transaction,
        Transaction.objects.create(
            user=user,
            account=account,
            type=type,
            amount=amount,
            currency_code=currency_code,
            amount_base=amount_base,
            base_currency=base_currency,
            fx_rate_snapshot=fx_rate_snapshot,
            category=category,
            date=date,
            description=description,
            reference=reference,
        ),
    )


def update_transaction(
    *,
    transaction: Transaction,
    user: AbstractBaseUser,
    fx_rate_override: Decimal | None = None,
    **fields: Any,
) -> Transaction:
    if transaction.user_id != user.pk:
        raise TransactionNotFoundError("Transaction not found.")

    fx_fields_changed = "amount" in fields or "currency_code" in fields

    if "category_id" in fields and fields["category_id"] is not None:
        _get_accessible_category(category_id=fields["category_id"], user=user)

    for attr, value in fields.items():
        setattr(transaction, attr, value)

    if fx_fields_changed:
        base_currency: str = user.default_currency_code  # type: ignore[attr-defined]
        transaction.base_currency = base_currency
        transaction.amount_base, transaction.fx_rate_snapshot = _compute_fx(
            amount=transaction.amount,
            currency_code=transaction.currency_code,
            base_currency=base_currency,
            tx_date=transaction.date,
            fx_rate_override=fx_rate_override,
        )

    transaction.save()
    return transaction


def soft_delete_transaction(*, transaction: Transaction, user: AbstractBaseUser) -> None:
    if transaction.user_id != user.pk:
        raise TransactionNotFoundError("Transaction not found.")
    transaction.soft_delete()
