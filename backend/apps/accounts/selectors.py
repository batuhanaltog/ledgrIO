from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.db.models import Case, Count, DecimalField, F, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import Coalesce

from apps.accounts.models import Account


def _balance_subquery() -> Subquery:
    from apps.transactions.models import Transaction

    return Subquery(
        Transaction.objects.filter(account=OuterRef("pk"))
        .values("account")
        .annotate(
            net=Sum(
                Case(
                    When(type="income", then=F("amount")),
                    When(type="expense", then=-F("amount")),
                    output_field=DecimalField(max_digits=20, decimal_places=8),
                )
            )
        )
        .values("net")
    )


def get_account_list_with_balance(
    *, user: Any, filters: dict[str, Any] | None = None
) -> Any:
    qs = Account.objects.filter(user=user).annotate(
        activity_net=Coalesce(
            _balance_subquery(),
            Decimal("0"),
            output_field=DecimalField(max_digits=20, decimal_places=8),
        ),
        current_balance=F("opening_balance") + F("activity_net"),
        transaction_count=Count("transactions", distinct=True),
    )
    filters = filters or {}
    if account_type := filters.get("account_type"):
        qs = qs.filter(account_type=account_type)
    if not filters.get("include_archived"):
        qs = qs.filter(is_active=True)
    if currency := filters.get("currency"):
        qs = qs.filter(currency_code=currency)
    return qs.order_by("name")


def get_account_with_balance(*, account_id: int, user: Any) -> Account:
    from common.exceptions import AccountNotFoundError

    qs = get_account_list_with_balance(user=user, filters={"include_archived": True})
    try:
        return cast(Account, qs.get(pk=account_id))
    except Account.DoesNotExist:
        raise AccountNotFoundError(f"Account {account_id} not found") from None


def get_total_assets_summary(*, user: Any) -> dict[str, Any]:
    from datetime import date

    from apps.currencies.services import RateNotFoundError, convert
    from apps.users.models import UserProfile

    accounts = get_account_list_with_balance(user=user, filters={"include_archived": True})
    try:
        profile = UserProfile.objects.get(user=user)
        base_currency: str = profile.user.default_currency_code or "USD"
    except UserProfile.DoesNotExist:
        base_currency = "USD"

    today = date.today()
    total = Decimal("0")
    stale_warning = False
    by_type: dict[str, Decimal] = {}

    for account in accounts:
        bal: Decimal = account.current_balance
        if account.currency_code != base_currency:
            try:
                bal = convert(amount=bal, from_code=account.currency_code, to_code=base_currency, at=today)
            except (RateNotFoundError, Exception):
                stale_warning = True
        total += bal
        by_type[account.account_type] = by_type.get(account.account_type, Decimal("0")) + bal

    return {
        "base_currency": base_currency,
        "total_assets": total,
        "by_account_type": [{"account_type": k, "total": v} for k, v in by_type.items()],
        "stale_fx_warning": stale_warning,
    }
