from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.budgets.models import Budget
from apps.budgets.tests.factories import BudgetFactory


@pytest.mark.django_db
def test_budget_model_fields_exist():
    fields = {f.name for f in Budget._meta.get_fields()}
    for field in ["name", "category", "amount", "date_from", "date_to",
                  "alert_threshold", "alert_sent_at", "user", "created_at", "updated_at"]:
        assert field in fields, f"Missing field: {field}"


@pytest.mark.django_db
def test_budget_amount_must_be_positive():
    with pytest.raises(IntegrityError):
        BudgetFactory(amount=Decimal("0.00000000"))


@pytest.mark.django_db
def test_budget_date_to_before_date_from_raises():
    with pytest.raises(IntegrityError):
        BudgetFactory(
            date_from=date(2026, 5, 31),
            date_to=date(2026, 5, 1),
        )


@pytest.mark.django_db
def test_budget_alert_threshold_above_one_raises():
    with pytest.raises(IntegrityError):
        BudgetFactory(alert_threshold=Decimal("1.10000000"))


@pytest.mark.django_db
def test_budget_alert_threshold_negative_raises():
    with pytest.raises(IntegrityError):
        BudgetFactory(alert_threshold=Decimal("-0.10000000"))


@pytest.mark.django_db
def test_budget_alert_threshold_can_be_null():
    b = BudgetFactory(alert_threshold=None)
    assert b.alert_threshold is None


@pytest.mark.django_db
def test_budget_category_can_be_null():
    b = BudgetFactory(category=None)
    assert b.category is None


@pytest.mark.django_db
def test_budget_str():
    b = BudgetFactory(name="Groceries", amount=Decimal("500.00000000"))
    assert "Groceries" in str(b)
