from __future__ import annotations

from datetime import date

from celery import shared_task
from django.db.utils import OperationalError


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=5,
)
def send_budget_alerts(target_date_iso: str | None = None) -> dict[str, int]:
    """
    Beat-scheduled daily at 07:00 UTC.
    Checks all active budgets with an alert threshold and sends email if threshold crossed.
    """
    from apps.budgets.selectors import get_all_active_budgets_for_alert
    from apps.budgets.services import check_and_send_budget_alerts

    today = date.fromisoformat(target_date_iso) if target_date_iso else date.today()
    budgets = list(get_all_active_budgets_for_alert(today=today))

    sent = 0
    for budget in budgets:
        if check_and_send_budget_alerts(budget=budget):
            sent += 1

    return {"sent": sent, "checked": len(budgets)}
