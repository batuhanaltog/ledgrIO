from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.db.models import Case, Count, DecimalField, F, QuerySet, Sum, When
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek

from .models import Transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

QUANTIZE = Decimal("0.00000001")

_ALLOWED_ORDERINGS = {"date", "-date", "amount", "-amount"}
_TRUNC_MAP = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}


def get_transaction_list(
    *,
    user: AbstractBaseUser,
    filters: dict[str, Any],
) -> QuerySet[Transaction]:
    qs = Transaction.objects.filter(user=user).select_related("category")

    if type_ := filters.get("type"):
        qs = qs.filter(type=type_)
    if category_id := filters.get("category"):
        qs = qs.filter(category_id=category_id)
    if currency := filters.get("currency"):
        qs = qs.filter(currency_code=currency)
    if date_from := filters.get("date_from"):
        qs = qs.filter(date__gte=date_from)
    if date_to := filters.get("date_to"):
        qs = qs.filter(date__lte=date_to)
    if amount_min := filters.get("amount_min"):
        qs = qs.filter(amount__gte=amount_min)
    if amount_max := filters.get("amount_max"):
        qs = qs.filter(amount__lte=amount_max)
    if search := filters.get("search"):
        qs = qs.filter(description__icontains=search)

    raw_ordering = filters.get("ordering", "-date")
    ordering: str = str(raw_ordering) if raw_ordering in _ALLOWED_ORDERINGS else "-date"
    return cast(QuerySet[Transaction], qs.order_by(ordering))


def get_transaction_summary(
    *,
    user: AbstractBaseUser,
    date_from: date_type,
    date_to: date_type,
    group_by: str = "day",
) -> dict[str, Any]:
    qs = Transaction.objects.filter(user=user, date__range=(date_from, date_to))

    totals = qs.aggregate(
        total_income=Sum(
            Case(
                When(type="income", then=F("amount_base")),
                default=Decimal("0"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            )
        ),
        total_expense=Sum(
            Case(
                When(type="expense", then=F("amount_base")),
                default=Decimal("0"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            )
        ),
    )
    total_income = (totals["total_income"] or Decimal("0")).quantize(QUANTIZE)
    total_expense = (totals["total_expense"] or Decimal("0")).quantize(QUANTIZE)

    by_category = list(
        qs.values("category_id", "category__name")
        .annotate(total=Sum("amount_base"), count=Count("id"))
        .order_by("-total")
    )

    trunc_fn = _TRUNC_MAP.get(group_by, TruncDay)
    period_rows = (
        qs.annotate(
            signed=Case(
                When(type="income", then=F("amount_base")),
                default=-F("amount_base"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            ),
            period=trunc_fn("date"),
        )
        .values("period")
        .annotate(period_net=Sum("signed"))
        .order_by("period")
    )

    cumulative = Decimal("0")
    running_balance = []
    for row in period_rows:
        cumulative += row["period_net"] or Decimal("0")
        running_balance.append(
            {
                "period": row["period"].isoformat() if row["period"] else None,
                "cumulative_net": str(cumulative.quantize(QUANTIZE)),
            }
        )

    return {
        "total_income": str(total_income),
        "total_expense": str(total_expense),
        "net": str((total_income - total_expense).quantize(QUANTIZE)),
        "by_category": by_category,
        "running_balance": running_balance,
    }
