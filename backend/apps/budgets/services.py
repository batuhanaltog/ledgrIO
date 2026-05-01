from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction as db_transaction
from django.db.models import Q
from django.utils import timezone

from apps.budgets.models import Budget
from apps.categories.models import Category
from common.exceptions import BudgetInvalidError

_UNSET = object()


def _validate_dates(date_from: Any, date_to: Any) -> None:
    if date_from is not None and date_to is not None and date_to < date_from:
        raise BudgetInvalidError("date_to must be on or after date_from.")


def _validate_category_ownership(*, category_id: int | None, user: Any) -> Any:
    if category_id is None:
        return None
    try:
        return Category.objects.get(Q(is_system=True) | Q(owner=user), pk=category_id)
    except Category.DoesNotExist:
        raise BudgetInvalidError(
            f"category {category_id} not found or not accessible."
        ) from None


def create_budget(*, user: Any, data: dict[str, Any]) -> Budget:
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    _validate_dates(date_from, date_to)

    category_id = data.pop("category_id", None)
    category = data.pop("category", None)
    if category_id is not None:
        category = _validate_category_ownership(category_id=category_id, user=user)

    return Budget.objects.create(user=user, category=category, **data)


def update_budget(*, budget: Budget, data: dict[str, Any]) -> Budget:
    effective_from = data.get("date_from", budget.date_from)
    effective_to = data.get("date_to", budget.date_to)
    _validate_dates(effective_from, effective_to)

    category_id = data.pop("category_id", _UNSET)
    if category_id is not _UNSET:
        data["category"] = _validate_category_ownership(category_id=category_id, user=budget.user)

    amount_changed = "amount" in data
    threshold_changed = "alert_threshold" in data

    for attr, value in data.items():
        setattr(budget, attr, value)

    if amount_changed or threshold_changed:
        budget.alert_sent_at = None

    budget.save()
    return budget


def delete_budget(*, budget: Budget) -> None:
    budget.delete()


def check_and_send_budget_alerts(*, budget: Budget) -> bool:
    """
    Idempotent alert check. Returns True only if email was sent this call.
    Guards: threshold None → skip. alert_sent_at set → skip. usage_pct < threshold → skip.
    Order: DB flag first, then email (fail_silently) — no double-send risk.
    """
    if budget.alert_threshold is None:
        return False
    if budget.alert_sent_at is not None:
        return False

    usage_pct: Decimal | None = getattr(budget, "usage_pct", Decimal("0"))
    if usage_pct is None or usage_pct < budget.alert_threshold:
        return False

    with db_transaction.atomic():
        Budget.objects.filter(pk=budget.pk).update(alert_sent_at=timezone.now())

    send_mail(
        subject=f"[Ledgr] Budget Alert: {budget.name}",
        message=(
            f"Your budget '{budget.name}' has reached "
            f"{float(usage_pct) * 100:.1f}% of its limit.\n\n"
            f"Spent: {getattr(budget, 'spent', '?')} / {budget.amount} "
            f"{budget.user.default_currency_code}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[budget.user.email],
        fail_silently=True,
    )

    return True
