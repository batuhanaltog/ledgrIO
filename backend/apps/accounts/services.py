from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.db import transaction as db_transaction

from apps.accounts.models import Account
from apps.currencies.models import Currency
from common.exceptions import AccountCurrencyLockedError, AccountInUseError


def create_account(
    *,
    user: Any,
    name: str,
    account_type: str,
    currency_code: str,
    opening_balance: Decimal = Decimal("0"),
    notes: str = "",
    is_active: bool = True,
) -> Account:
    if not Currency.objects.filter(code=currency_code).exists():
        raise ValueError(f"Unknown currency code: {currency_code}")
    return cast(Account, Account.objects.create(
        user=user,
        name=name,
        account_type=account_type,
        currency_code=currency_code,
        opening_balance=opening_balance,
        notes=notes,
        is_active=is_active,
    ))


def update_account(*, account: Account, **fields: Any) -> Account:
    if "currency_code" in fields and account.transactions.exists():
        raise AccountCurrencyLockedError(
            "Cannot change currency once transactions exist on this account."
        )
    for attr, value in fields.items():
        setattr(account, attr, value)
    account.save()
    return account


def soft_delete_account(*, account: Account) -> None:
    if account.transactions.exists():
        raise AccountInUseError(
            "Cannot delete account with linked transactions. Reassign them first."
        )
    account.soft_delete()


def reassign_transactions(*, source_account: Account, target_account: Account) -> int:
    from apps.transactions.models import Transaction

    count: int = Transaction.objects.filter(account=source_account).update(
        account=target_account
    )
    return count
