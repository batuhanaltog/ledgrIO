from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet

from apps.recurring.models import RecurringTemplate
from common.exceptions import RecurringTemplateNotFoundError


def get_recurring_template_list(
    *,
    user: Any,
    filters: dict[str, Any] | None = None,
) -> QuerySet[RecurringTemplate]:
    qs = RecurringTemplate.objects.filter(user=user).select_related("account", "category")

    filters = filters or {}
    if type_ := filters.get("type"):
        qs = qs.filter(type=type_)
    if "is_active" in filters:
        qs = qs.filter(is_active=filters["is_active"])
    if account_id := filters.get("account_id"):
        qs = qs.filter(account_id=account_id)
    if frequency := filters.get("frequency"):
        qs = qs.filter(frequency=frequency)

    return cast(QuerySet[RecurringTemplate], qs.order_by("description"))


def get_recurring_template_detail(
    *,
    template_id: int,
    user: Any,
) -> RecurringTemplate:
    try:
        return cast(
            RecurringTemplate,
            RecurringTemplate.objects.filter(user=user)
            .select_related("account", "category")
            .get(pk=template_id),
        )
    except RecurringTemplate.DoesNotExist:
        raise RecurringTemplateNotFoundError(
            f"RecurringTemplate {template_id} not found."
        ) from None
