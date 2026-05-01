from __future__ import annotations

from datetime import date

from celery import shared_task
from django.db.utils import OperationalError


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=5,
)
def materialize_due_recurring_transactions(
    target_date_iso: str | None = None,
) -> dict[str, int]:
    """
    Beat-scheduled daily at 03:00 UTC.
    Iterates all active templates, materializes those whose next due date has
    arrived, and returns a summary dict.
    """
    from apps.recurring.models import RecurringTemplate
    from apps.recurring.services import compute_next_due_date, materialize_template_for_date

    target = date.fromisoformat(target_date_iso) if target_date_iso else date.today()
    templates = (
        RecurringTemplate.objects.filter(is_active=True)
        .select_related("account", "user", "category")
    )

    materialized = 0
    skipped = 0

    for template in templates:
        next_due = compute_next_due_date(template=template)
        if next_due is not None and next_due <= target:
            result = materialize_template_for_date(
                template=template, target_date=next_due
            )
            if result is not None:
                materialized += 1
            else:
                skipped += 1
        else:
            skipped += 1

    return {"materialized": materialized, "skipped": skipped}
