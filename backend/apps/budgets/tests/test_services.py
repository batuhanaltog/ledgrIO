from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError

from apps.budgets.models import Budget
from apps.budgets.tasks import send_budget_alerts
from apps.budgets.tests.factories import BudgetFactory
from apps.categories.tests.factories import CategoryFactory
from apps.users.tests.factories import UserFactory
from common.exceptions import BudgetInvalidError


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

from apps.accounts.tests.factories import AccountFactory
from apps.budgets.selectors import get_budget_for_user, get_budget_queryset
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


# ---------------------------------------------------------------------------
# Service tests — create_budget
# ---------------------------------------------------------------------------

from apps.budgets.services import create_budget, delete_budget, update_budget


@pytest.mark.django_db
def test_create_budget_happy_path():
    user = UserFactory()

    budget = create_budget(user=user, data={
        "name": "Groceries",
        "category": None,
        "amount": Decimal("500.00000000"),
        "date_from": date(2026, 5, 1),
        "date_to": date(2026, 5, 31),
        "alert_threshold": Decimal("0.80000000"),
    })

    assert budget.pk is not None
    assert budget.name == "Groceries"
    assert budget.user == user


@pytest.mark.django_db
def test_create_budget_date_to_before_date_from_raises():
    user = UserFactory()

    with pytest.raises(BudgetInvalidError, match="date_to"):
        create_budget(user=user, data={
            "name": "Bad dates",
            "category": None,
            "amount": Decimal("100.00000000"),
            "date_from": date(2026, 5, 31),
            "date_to": date(2026, 5, 1),
        })


@pytest.mark.django_db
def test_create_budget_category_not_owned_raises():
    user = UserFactory()
    other = UserFactory()
    cat = CategoryFactory(owner=other)

    with pytest.raises(BudgetInvalidError, match="category"):
        create_budget(user=user, data={
            "name": "Bad category",
            "category_id": cat.pk,
            "amount": Decimal("100.00000000"),
            "date_from": date(2026, 5, 1),
            "date_to": date(2026, 5, 31),
        })


# ---------------------------------------------------------------------------
# Service tests — update_budget
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_update_budget_changes_name():
    user = UserFactory()
    budget = BudgetFactory(user=user, name="Old")

    updated = update_budget(budget=budget, data={"name": "New"})

    assert updated.name == "New"


@pytest.mark.django_db
def test_update_budget_resets_alert_sent_at_when_amount_changes():
    from django.utils import timezone

    user = UserFactory()
    budget = BudgetFactory(
        user=user,
        amount=Decimal("500.00000000"),
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=timezone.now(),
    )

    updated = update_budget(budget=budget, data={"amount": Decimal("1000.00000000")})

    assert updated.alert_sent_at is None


@pytest.mark.django_db
def test_update_budget_resets_alert_sent_at_when_threshold_changes():
    from django.utils import timezone

    user = UserFactory()
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=timezone.now(),
    )

    updated = update_budget(budget=budget, data={"alert_threshold": Decimal("0.90000000")})

    assert updated.alert_sent_at is None


@pytest.mark.django_db
def test_update_budget_does_not_reset_alert_sent_at_when_name_only_changes():
    from django.utils import timezone

    user = UserFactory()
    sent_at = timezone.now()
    budget = BudgetFactory(user=user, alert_threshold=Decimal("0.80000000"), alert_sent_at=sent_at)

    updated = update_budget(budget=budget, data={"name": "Renamed"})

    assert updated.alert_sent_at == sent_at


# ---------------------------------------------------------------------------
# Service tests — delete_budget
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_budget_removes_record():
    user = UserFactory()
    budget = BudgetFactory(user=user)
    pk = budget.pk

    delete_budget(budget=budget)

    assert not Budget.objects.filter(pk=pk).exists()


# ---------------------------------------------------------------------------
# Alert service tests
# ---------------------------------------------------------------------------

from apps.budgets.services import check_and_send_budget_alerts


@pytest.mark.django_db
def test_alert_not_sent_when_threshold_is_none():
    user = UserFactory()
    budget = BudgetFactory(user=user, alert_threshold=None)
    budget.usage_pct = Decimal("0.90000000")

    result = check_and_send_budget_alerts(budget=budget)

    assert result is False


@pytest.mark.django_db
def test_alert_not_sent_when_already_sent():
    from django.utils import timezone

    user = UserFactory()
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=timezone.now(),
    )
    budget.usage_pct = Decimal("0.95000000")

    result = check_and_send_budget_alerts(budget=budget)

    assert result is False


@pytest.mark.django_db
def test_alert_not_sent_when_below_threshold():
    user = UserFactory()
    budget = BudgetFactory(user=user, alert_threshold=Decimal("0.80000000"))
    budget.usage_pct = Decimal("0.70000000")

    result = check_and_send_budget_alerts(budget=budget)

    assert result is False


@pytest.mark.django_db
def test_alert_sent_when_at_threshold_boundary():
    user = UserFactory()
    user.email = "test@ledgr.io"
    user.save()
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    budget.usage_pct = Decimal("0.80000000")
    budget.spent = Decimal("400.00000000")

    with patch("apps.budgets.services.send_mail") as mock_mail:
        result = check_and_send_budget_alerts(budget=budget)

    assert result is True
    mock_mail.assert_called_once()
    refreshed = Budget.objects.get(pk=budget.pk)
    assert refreshed.alert_sent_at is not None


@pytest.mark.django_db
def test_alert_idempotent_second_call_skipped():
    user = UserFactory()
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    budget.usage_pct = Decimal("0.90000000")
    budget.spent = Decimal("450.00000000")

    with patch("apps.budgets.services.send_mail"):
        check_and_send_budget_alerts(budget=budget)

    # Reload from DB — alert_sent_at is now set
    budget_reloaded = Budget.objects.get(pk=budget.pk)
    budget_reloaded.usage_pct = Decimal("0.90000000")

    with patch("apps.budgets.services.send_mail") as mock_mail_2:
        result = check_and_send_budget_alerts(budget=budget_reloaded)

    assert result is False
    mock_mail_2.assert_not_called()


# ---------------------------------------------------------------------------
# Beat task tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_send_budget_alerts_task_skips_when_below_threshold():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    today = date.today()
    BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=today.replace(day=1),
        date_to=today.replace(day=28),
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    # 30% spent — below 80% threshold
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("300.00000000"), amount_base=Decimal("300.00000000"),
        currency_code="USD", base_currency="USD", date=today,
    )

    with patch("apps.budgets.services.send_mail") as mock_mail:
        result = send_budget_alerts()

    assert result["sent"] == 0
    mock_mail.assert_not_called()


@pytest.mark.django_db
def test_send_budget_alerts_task_sends_when_above_threshold():
    user = UserFactory()
    user.email = "owner@ledgr.io"
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    today = date.today()
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=today.replace(day=1),
        date_to=today.replace(day=28),
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    # 90% spent — above threshold
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("900.00000000"), amount_base=Decimal("900.00000000"),
        currency_code="USD", base_currency="USD", date=today,
    )

    with patch("apps.budgets.services.send_mail") as mock_mail:
        result = send_budget_alerts()

    assert result["sent"] == 1
    mock_mail.assert_called_once()
    assert Budget.objects.get(pk=budget.pk).alert_sent_at is not None
