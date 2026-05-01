from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any, cast

from django.db.models import DecimalField, OuterRef, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from apps.debts.models import Debt, DebtCategory, DebtPayment
from common.exceptions import DebtNotFoundError


def _build_tree(
    categories: list[DebtCategory],
    parent_id: int | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for cat in categories:
        if cat.parent_id == parent_id:
            node: dict[str, Any] = {
                "id": cat.pk,
                "name": cat.name,
                "parent_id": cat.parent_id,
                "children": _build_tree(categories, cat.pk),
            }
            result.append(node)
    return result


def get_debt_categories_tree(*, user: Any) -> list[dict[str, Any]]:
    categories = list(DebtCategory.objects.filter(user=user).order_by("name"))
    return _build_tree(categories, parent_id=None)


def get_debt_list(
    *, user: Any, filters: dict[str, Any] | None = None
) -> QuerySet[Debt]:
    qs = Debt.objects.filter(user=user).select_related("category")
    filters = filters or {}

    if category_id := filters.get("category_id"):
        qs = qs.filter(category_id=category_id)
    if currency := filters.get("currency"):
        qs = qs.filter(currency_code=currency)
    if "is_settled" in filters and filters["is_settled"] is not None:
        qs = qs.filter(is_settled=filters["is_settled"])

    return cast(QuerySet[Debt], qs.order_by("name"))


def get_debt_with_payments(*, debt_id: int, user: Any) -> Debt:
    try:
        return cast(
            Debt,
            Debt.objects.filter(user=user)
            .prefetch_related("payments__transaction")
            .get(pk=debt_id),
        )
    except Debt.DoesNotExist:
        raise DebtNotFoundError(f"Debt {debt_id} not found.") from None


def get_debt_monthly_summary(*, user: Any, year: int, month: int) -> dict[str, Any]:
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    paid_subquery = (
        DebtPayment.objects.filter(
            debt=OuterRef("pk"),
            paid_at__range=(month_start, month_end),
        )
        .values("debt")
        .annotate(total=Sum("amount"))
        .values("total")
    )

    debts = (
        Debt.objects.filter(user=user)
        .annotate(
            paid_this_month=Coalesce(
                Subquery(paid_subquery),
                Decimal("0"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            )
        )
        .select_related("category")
    )

    expected_total = Decimal("0")
    paid_total = Decimal("0")
    by_category: dict[str | None, dict[str, Any]] = {}

    for debt in debts:
        if debt.is_settled:
            continue

        expected_total += debt.expected_monthly_payment
        paid_total += debt.paid_this_month  
        cat_key = debt.category.name if debt.category else None
        if cat_key not in by_category:
            by_category[cat_key] = {
                "category": cat_key,
                "expected": Decimal("0"),
                "paid": Decimal("0"),
            }
        by_category[cat_key]["expected"] += debt.expected_monthly_payment
        by_category[cat_key]["paid"] += debt.paid_this_month  
    remaining_total = expected_total - paid_total

    monthly_income: Decimal | None = None
    leftover_after_expected_debts: Decimal | None = None

    try:
        from apps.users.models import UserProfile

        profile = UserProfile.objects.select_related("user").get(user=user)
        if hasattr(profile, "monthly_income") and profile.monthly_income is not None:
            monthly_income = profile.monthly_income
            leftover_after_expected_debts = monthly_income - expected_total
    except Exception:
        pass

    return {
        "month": f"{year}-{month:02d}",
        "expected_total": expected_total,
        "paid_total": paid_total,
        "remaining_total": remaining_total,
        "monthly_income": monthly_income,
        "leftover_after_expected_debts": leftover_after_expected_debts,
        "by_category": list(by_category.values()),
    }
