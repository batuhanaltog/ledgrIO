from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.budgets.models import Budget
from apps.budgets.tests.factories import BudgetFactory
from apps.users.tests.factories import UserFactory
from apps.categories.tests.factories import CategoryFactory


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


# ---------------------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------------------

from apps.budgets.selectors import get_budget_for_user, get_budget_queryset
from apps.accounts.tests.factories import AccountFactory
from apps.currencies.tests.factories import CurrencyFactory
from apps.transactions.tests.factories import TransactionFactory
from common.exceptions import BudgetNotFoundError


@pytest.mark.django_db
def test_get_budget_queryset_annotates_spent_zero_when_no_transactions():
    user = UserFactory()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(
        user=user,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    qs = get_budget_queryset(user=user)
    result = qs.get(pk=budget.pk)

    assert result.spent == Decimal("0")
    assert result.remaining == budget.amount
    assert result.usage_pct == Decimal("0")


@pytest.mark.django_db
def test_get_budget_queryset_annotates_spent_from_transactions():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        category=None,
    )
    TransactionFactory(
        user=user,
        account=account,
        type="expense",
        amount=Decimal("300.00000000"),
        amount_base=Decimal("300.00000000"),
        base_currency="USD",
        currency_code="USD",
        date=date(2026, 5, 15),
    )

    qs = get_budget_queryset(user=user)
    result = qs.get(pk=budget.pk)

    assert result.spent == Decimal("300.00000000")
    assert result.remaining == Decimal("700.00000000")
    assert result.usage_pct == Decimal("0.3")


@pytest.mark.django_db
def test_get_budget_queryset_category_specific_budget_excludes_other_categories():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    cat_food = CategoryFactory(owner=user)
    cat_rent = CategoryFactory(owner=user)
    budget = BudgetFactory(
        user=user,
        amount=Decimal("500.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        category=cat_food,
    )
    # This one should count
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("100.00000000"), amount_base=Decimal("100.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_food, date=date(2026, 5, 10),
    )
    # This one should NOT count (different category)
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("200.00000000"), amount_base=Decimal("200.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_rent, date=date(2026, 5, 10),
    )

    result = get_budget_queryset(user=user).get(pk=budget.pk)

    assert result.spent == Decimal("100.00000000")


@pytest.mark.django_db
def test_get_budget_queryset_null_category_sums_all_categories():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    cat_food = CategoryFactory(owner=user)
    cat_rent = CategoryFactory(owner=user)
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        category=None,
    )
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("100.00000000"), amount_base=Decimal("100.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_food, date=date(2026, 5, 10),
    )
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("200.00000000"), amount_base=Decimal("200.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_rent, date=date(2026, 5, 10),
    )

    result = get_budget_queryset(user=user).get(pk=budget.pk)

    assert result.spent == Decimal("300.00000000")


@pytest.mark.django_db
def test_get_budget_queryset_excludes_transactions_outside_date_range():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    budget = BudgetFactory(
        user=user,
        amount=Decimal("500.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )
    # Outside range — should not count
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("300.00000000"), amount_base=Decimal("300.00000000"),
        currency_code="USD", base_currency="USD",
        date=date(2026, 4, 30),
    )

    result = get_budget_queryset(user=user).get(pk=budget.pk)

    assert result.spent == Decimal("0")


@pytest.mark.django_db
def test_get_budget_queryset_only_returns_requesting_users_budgets():
    user = UserFactory()
    other_user = UserFactory()
    BudgetFactory(user=other_user)
    BudgetFactory(user=user)

    qs = get_budget_queryset(user=user)

    assert qs.count() == 1


@pytest.mark.django_db
def test_get_budget_for_user_raises_not_found_for_other_user():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    with pytest.raises(BudgetNotFoundError):
        get_budget_for_user(user=user, pk=budget.pk)
