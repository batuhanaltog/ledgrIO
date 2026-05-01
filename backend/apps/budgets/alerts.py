from decimal import Decimal
from common.utils.decimal_utils import percentage, ZERO


def check_budget_thresholds(budget, actual_spend: Decimal) -> list[int]:
    """
    Returns a list of threshold percentages that have been crossed.
    Pure function — no DB access, easy to unit test.
    """
    if budget.amount_limit == ZERO:
        return []

    pct = percentage(actual_spend, budget.amount_limit)
    triggered = []

    if budget.alert_at_50 and pct >= Decimal("50"):
        triggered.append(50)
    if budget.alert_at_80 and pct >= Decimal("80"):
        triggered.append(80)
    if budget.alert_at_100 and pct >= Decimal("100"):
        triggered.append(100)

    return triggered


def compute_budget_status(budget, actual_spend: Decimal) -> dict:
    """Returns a dict with budget status details."""
    pct = percentage(actual_spend, budget.amount_limit) if budget.amount_limit else ZERO
    remaining = budget.amount_limit - actual_spend
    return {
        "budget_id": str(budget.id),
        "category": budget.category.name,
        "limit": float(budget.amount_limit),
        "spent": float(actual_spend),
        "remaining": float(remaining),
        "percent_used": float(pct),
        "is_over_budget": actual_spend > budget.amount_limit,
    }
