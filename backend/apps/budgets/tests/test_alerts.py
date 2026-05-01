import pytest
from decimal import Decimal
from apps.budgets.alerts import check_budget_thresholds, compute_budget_status
from .factories import BudgetFactory


@pytest.mark.django_db
class TestCheckBudgetThresholds:
    def test_no_alert_below_50(self):
        budget = BudgetFactory(amount_limit=Decimal("100"))
        assert check_budget_thresholds(budget, Decimal("49")) == []

    def test_triggers_50_alert(self):
        budget = BudgetFactory(amount_limit=Decimal("100"))
        assert 50 in check_budget_thresholds(budget, Decimal("50"))

    def test_triggers_80_alert(self):
        budget = BudgetFactory(amount_limit=Decimal("100"))
        result = check_budget_thresholds(budget, Decimal("80"))
        assert 50 in result
        assert 80 in result

    def test_triggers_100_alert(self):
        budget = BudgetFactory(amount_limit=Decimal("100"))
        result = check_budget_thresholds(budget, Decimal("100"))
        assert 50 in result
        assert 80 in result
        assert 100 in result

    def test_over_budget_triggers_all(self):
        budget = BudgetFactory(amount_limit=Decimal("100"))
        result = check_budget_thresholds(budget, Decimal("150"))
        assert 100 in result

    def test_zero_limit_no_alerts(self):
        budget = BudgetFactory(amount_limit=Decimal("0"))
        assert check_budget_thresholds(budget, Decimal("100")) == []

    def test_disabled_alert_not_triggered(self):
        budget = BudgetFactory(amount_limit=Decimal("100"), alert_at_50=False, alert_at_80=False)
        result = check_budget_thresholds(budget, Decimal("90"))
        assert 50 not in result
        assert 80 not in result


@pytest.mark.django_db
class TestComputeBudgetStatus:
    def test_over_budget_flag(self):
        budget = BudgetFactory(amount_limit=Decimal("100"))
        status = compute_budget_status(budget, Decimal("120"))
        assert status["is_over_budget"] is True
        assert status["remaining"] == -20.0

    def test_within_budget(self):
        budget = BudgetFactory(amount_limit=Decimal("500"))
        status = compute_budget_status(budget, Decimal("200"))
        assert status["is_over_budget"] is False
        assert status["percent_used"] == 40.0
        assert status["remaining"] == 300.0
