from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.db import transaction as db_transaction

from apps.currencies.models import Currency
from apps.currencies.services import get_exchange_rate
from apps.debts.models import Debt, DebtCategory, DebtPayment
from common.exceptions import (
    DebtBalanceUnderflowError,
    DebtCategoryCycleError,
    DebtCategoryHasChildrenError,
    DebtCategoryNotFoundError,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.accounts.models import Account

QUANTIZE = Decimal("0.00000001")
MAX_DEBT_CATEGORY_DEPTH = 5


def _get_category_depth(category: DebtCategory) -> int:
    depth = 0
    current = category
    while current.parent_id is not None:
        depth += 1
        current = current.parent  # type: ignore[assignment]
        if depth > MAX_DEBT_CATEGORY_DEPTH:
            break
    return depth


def _would_create_cycle(category: DebtCategory, new_parent_id: int) -> bool:
    """Return True if setting new_parent_id as category's parent would create a cycle."""
    if new_parent_id == category.pk:
        return True
    visited: set[int] = set()
    current_id: int | None = new_parent_id
    while current_id is not None:
        if current_id == category.pk:
            return True
        if current_id in visited:
            break
        visited.add(current_id)
        try:
            parent = DebtCategory.objects.get(pk=current_id)
            current_id = parent.parent_id
        except DebtCategory.DoesNotExist:
            break
    return False


def create_debt_category(
    *,
    user: AbstractBaseUser,
    name: str,
    parent_id: int | None = None,
) -> DebtCategory:
    parent: DebtCategory | None = None
    if parent_id is not None:
        try:
            parent = DebtCategory.objects.get(pk=parent_id, user=user)
        except DebtCategory.DoesNotExist:
            raise DebtCategoryNotFoundError(
                f"Debt category {parent_id} not found."
            ) from None

        depth = _get_category_depth(cast(DebtCategory, parent)) + 1
        if depth >= MAX_DEBT_CATEGORY_DEPTH:
            from common.exceptions import CategoryDepthError
            raise CategoryDepthError(
                f"Category hierarchy cannot exceed depth {MAX_DEBT_CATEGORY_DEPTH}."
            )

    return cast(DebtCategory, DebtCategory.objects.create(user=user, name=name, parent=parent))


def update_debt_category(*, category: DebtCategory, **fields: Any) -> DebtCategory:
    if "parent_id" in fields:
        new_parent_id: int | None = fields["parent_id"]
        if new_parent_id is not None:
            if _would_create_cycle(category, new_parent_id):
                raise DebtCategoryCycleError(
                    "Setting this parent would create a cycle in the debt category tree."
                )
            try:
                new_parent = DebtCategory.objects.get(pk=new_parent_id, user=category.user)
            except DebtCategory.DoesNotExist:
                raise DebtCategoryNotFoundError(
                    f"Debt category {new_parent_id} not found."
                ) from None

            prospective_depth = _get_category_depth(new_parent) + 1
            if prospective_depth >= MAX_DEBT_CATEGORY_DEPTH:
                from common.exceptions import CategoryDepthError
                raise CategoryDepthError(
                    f"Category hierarchy cannot exceed depth {MAX_DEBT_CATEGORY_DEPTH}."
                )
            fields = {**fields, "parent": new_parent}
            del fields["parent_id"]
        else:
            fields = {**fields, "parent": None}
            del fields["parent_id"]

    for attr, value in fields.items():
        setattr(category, attr, value)
    category.save()
    return category


def soft_delete_debt_category(*, category: DebtCategory) -> None:
    if category.children.filter(deleted_at__isnull=True).exists():
        raise DebtCategoryHasChildrenError(
            "Cannot delete a debt category that has child categories."
        )
    category.soft_delete()


def create_debt(
    *,
    user: AbstractBaseUser,
    category_id: int | None,
    name: str,
    original_amount: Decimal,
    expected_monthly_payment: Decimal,
    currency_code: str,
    interest_rate_pct: Decimal | None = None,
    due_day: int | None = None,
    notes: str = "",
) -> Debt:
    if not Currency.objects.filter(code=currency_code).exists():
        raise ValueError(f"Unknown currency code: {currency_code}")

    category: DebtCategory | None = None
    if category_id is not None:
        try:
            category = DebtCategory.objects.get(pk=category_id, user=user)
        except DebtCategory.DoesNotExist:
            raise DebtCategoryNotFoundError(
                f"Debt category {category_id} not found."
            ) from None

    return cast(Debt, Debt.objects.create(
        user=user,
        category=category,
        name=name,
        original_amount=original_amount,
        current_balance=original_amount,
        expected_monthly_payment=expected_monthly_payment,
        currency_code=currency_code,
        interest_rate_pct=interest_rate_pct,
        due_day=due_day,
        notes=notes,
    ))


def update_debt(*, debt: Debt, **fields: Any) -> Debt:
    # current_balance is managed by record/reverse_debt_payment; not directly editable.
    fields.pop("current_balance", None)

    if "category_id" in fields:
        new_cat_id: int | None = fields.pop("category_id")
        if new_cat_id is not None:
            try:
                fields["category"] = DebtCategory.objects.get(pk=new_cat_id, user=debt.user)
            except DebtCategory.DoesNotExist:
                raise DebtCategoryNotFoundError(
                    f"Debt category {new_cat_id} not found."
                ) from None
        else:
            fields["category"] = None

    for attr, value in fields.items():
        setattr(debt, attr, value)
    debt.save()
    return debt


def soft_delete_debt(*, debt: Debt) -> None:
    if debt.payments.exists():
        from rest_framework.exceptions import ValidationError
        raise ValidationError(
            "Cannot delete a debt that has payment records. Reverse payments first."
        )
    debt.soft_delete()


@db_transaction.atomic
def record_debt_payment(
    *,
    debt: Debt,
    account: Account,
    amount: Decimal,
    paid_at: date_type,
    user: AbstractBaseUser,
    description: str = "",
) -> DebtPayment:
    """
    Atomically create a Transaction + DebtPayment and reduce the debt balance.

    If the account currency differs from the debt currency, the transaction amount
    is converted to the account's currency using the FX snapshot at paid_at.
    The DebtPayment always stores the amount in the debt's own currency.
    """
    if amount > debt.current_balance:
        raise DebtBalanceUnderflowError(
            f"Payment amount {amount} exceeds current balance {debt.current_balance}."
        )

    if account.currency_code != debt.currency_code:
        tx_amount = (
            amount
            * get_exchange_rate(debt.currency_code, account.currency_code, at=paid_at)
        ).quantize(QUANTIZE)
        tx_currency = account.currency_code
    else:
        tx_amount = amount
        tx_currency = debt.currency_code

    base_currency: str = user.default_currency_code  # type: ignore[attr-defined]
    if tx_currency == base_currency:
        amount_base = tx_amount
        fx_rate_snapshot = Decimal("1")
    else:
        fx_rate_snapshot = get_exchange_rate(tx_currency, base_currency, at=paid_at)
        amount_base = (tx_amount * fx_rate_snapshot).quantize(QUANTIZE)

    tx_description = description or f"Debt payment: {debt.name}"

    from apps.transactions.models import EXPENSE, Transaction

    transaction = Transaction.objects.create(
        user=user,
        account=account,
        type=EXPENSE,
        amount=tx_amount,
        currency_code=tx_currency,
        amount_base=amount_base,
        base_currency=base_currency,
        fx_rate_snapshot=fx_rate_snapshot,
        category=None,
        date=paid_at,
        description=tx_description,
        reference="",
    )

    payment = DebtPayment.objects.create(
        debt=debt,
        transaction=transaction,
        amount=amount,
        paid_at=paid_at,
    )

    debt.current_balance -= amount
    if debt.current_balance == Decimal("0"):
        debt.is_settled = True
    debt.save(update_fields=["current_balance", "is_settled"])

    return payment


@db_transaction.atomic
def reverse_debt_payment(*, payment: DebtPayment) -> None:
    """
    Atomically soft-delete the linked transaction, restore the debt balance,
    and hard-delete the payment record.
    """
    debt = payment.debt

    payment.transaction.soft_delete()

    debt.current_balance += payment.amount
    if debt.is_settled:
        debt.is_settled = False
    debt.save(update_fields=["current_balance", "is_settled"])

    payment.delete()
