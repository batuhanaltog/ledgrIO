import logging
from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def check_budget_alerts_task():
    """Periodic task: check all active budgets and create notifications for threshold crossings."""
    from apps.budgets.models import Budget
    from apps.budgets.alerts import check_budget_thresholds
    from apps.transactions.models import Transaction
    from apps.notifications.models import Notification

    today = timezone.now().date()
    budgets = Budget.objects.filter(is_active=True).select_related("user", "category")

    for budget in budgets:
        if budget.period == Budget.Period.MONTHLY:
            period_start = today.replace(day=1)
        elif budget.period == Budget.Period.WEEKLY:
            period_start = today - timezone.timedelta(days=today.weekday())
        else:
            period_start = today

        actual_spend = (
            Transaction.objects.filter(
                user=budget.user,
                category=budget.category,
                transaction_type=Transaction.TransactionType.EXPENSE,
                transaction_date__gte=period_start,
            ).aggregate(total=Sum("amount"))["total"] or 0
        )

        thresholds = check_budget_thresholds(budget, actual_spend)
        for threshold in thresholds:
            already_notified = Notification.objects.filter(
                user=budget.user,
                notification_type=Notification.NotificationType.BUDGET_ALERT,
                metadata__budget_id=str(budget.id),
                metadata__threshold=threshold,
                created_at__date=today,
            ).exists()

            if not already_notified:
                Notification.objects.create(
                    user=budget.user,
                    notification_type=Notification.NotificationType.BUDGET_ALERT,
                    title=f"Budget Alert: {budget.category.name}",
                    message=f"You have used {threshold}% of your {budget.period.lower()} budget for {budget.category.name}.",
                    metadata={
                        "budget_id": str(budget.id),
                        "threshold": threshold,
                        "category": budget.category.name,
                    },
                )
                logger.info("Budget alert created: user=%s category=%s threshold=%s", budget.user.email, budget.category.name, threshold)
