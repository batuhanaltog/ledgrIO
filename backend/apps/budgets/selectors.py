from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    When,
)
from django.db.models.functions import Coalesce, NullIf

from apps.budgets.models import Budget
from apps.transactions.models import Transaction
from common.exceptions import BudgetNotFoundError

DECIMAL_FIELD: DecimalField = DecimalField(max_digits=20, decimal_places=8)
_ZERO = Decimal("0")


def _spent_annotation() -> Case:
    """
    Computes spent differently for category-specific vs. all-category (null) budgets.
    Only expense transactions within the budget's date range are counted.
    Uses amount_base (already in user's base currency).
    """
    category_subq = (
        Transaction.objects.filter(
            user=OuterRef("user"),
            category=OuterRef("category"),
            type="expense",
            date__gte=OuterRef("date_from"),
            date__lte=OuterRef("date_to"),
        )
        .values("user")
        .annotate(total=Sum("amount_base"))
        .values("total")
    )

    all_cats_subq = (
        Transaction.objects.filter(
            user=OuterRef("user"),
            type="expense",
            date__gte=OuterRef("date_from"),
            date__lte=OuterRef("date_to"),
        )
        .values("user")
        .annotate(total=Sum("amount_base"))
        .values("total")
    )

    return Case(
        When(
            category__isnull=True,
            then=Coalesce(Subquery(all_cats_subq), _ZERO, output_field=DECIMAL_FIELD),
        ),
        default=Coalesce(Subquery(category_subq), _ZERO, output_field=DECIMAL_FIELD),
        output_field=DECIMAL_FIELD,
    )


def get_budget_queryset(*, user: Any) -> QuerySet[Budget]:
    spent = _spent_annotation()
    return (
        Budget.objects.filter(user=user)
        .select_related("category")
        .annotate(spent=spent)
        .annotate(
            remaining=ExpressionWrapper(F("amount") - F("spent"), output_field=DECIMAL_FIELD),
            usage_pct=ExpressionWrapper(
                F("spent") / NullIf(F("amount"), _ZERO), output_field=DECIMAL_FIELD
            ),
        )
        .order_by("-date_from", "name")
    )


def get_budget_for_user(*, user: Any, pk: int) -> Budget:
    try:
        return get_budget_queryset(user=user).get(pk=pk)
    except Budget.DoesNotExist:
        raise BudgetNotFoundError(f"Budget {pk} not found.") from None


def get_all_active_budgets_for_alert(*, today: date) -> QuerySet[Budget]:
    """
    Returns budgets where today is in range, threshold is set, and alert not yet sent.
    """
    spent = _spent_annotation()
    return (
        Budget.objects.filter(
            date_from__lte=today,
            date_to__gte=today,
            alert_threshold__isnull=False,
            alert_sent_at__isnull=True,
        )
        .select_related("user", "category")
        .annotate(spent=spent)
        .annotate(
            remaining=ExpressionWrapper(F("amount") - F("spent"), output_field=DECIMAL_FIELD),
            usage_pct=ExpressionWrapper(
                F("spent") / NullIf(F("amount"), _ZERO), output_field=DECIMAL_FIELD
            ),
        )
    )
