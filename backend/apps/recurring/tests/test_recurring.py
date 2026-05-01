from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import AccountFactory
from apps.categories.tests.factories import CategoryFactory
from apps.currencies.tests.factories import CurrencyFactory
from apps.recurring.models import RecurringTemplate
from apps.recurring.services import compute_next_due_date, materialize_template_for_date
from apps.recurring.tasks import materialize_due_recurring_transactions
from apps.transactions.models import Transaction
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_template(user=None, account=None, **overrides) -> RecurringTemplate:
    """Create a minimal valid RecurringTemplate in the DB.

    Defaults to USD currency so it matches the User.default_currency_code
    default ("USD") and no FX lookup is needed unless the caller explicitly
    passes a different currency_code together with a seeded FxRate.
    """
    if user is None:
        user = UserFactory()
    if account is None:
        account = AccountFactory(user=user, currency_code="USD")

    defaults = dict(
        user=user,
        type="expense",
        amount=Decimal("100.00000000"),
        currency_code="USD",
        account=account,
        description="Test template",
        frequency="monthly",
        day_of_period=5,
        start_date=date(2025, 1, 1),
        is_active=True,
    )
    defaults.update(overrides)
    return RecurringTemplate.objects.create(**defaults)


def _auth_header(user) -> dict:
    token = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_recurring_template_amount_positive_constraint():
    """Negative amount violates DB check constraint and raises IntegrityError."""
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="TRY")
    with pytest.raises(IntegrityError):
        RecurringTemplate.objects.create(
            user=user,
            type="expense",
            amount=Decimal("-50.00000000"),
            currency_code="TRY",
            account=account,
            description="Bad template",
            frequency="monthly",
            day_of_period=5,
            start_date=date(2025, 1, 1),
        )


# ---------------------------------------------------------------------------
# compute_next_due_date tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_compute_next_due_monthly_basic():
    """Monthly template with no prior generation returns start_date itself when
    start_date equals day_of_period day."""
    template = _make_template(
        frequency="monthly",
        day_of_period=5,
        start_date=date(2025, 1, 5),
        last_generated_date=None,
    )
    result = compute_next_due_date(template=template)
    # reference = start_date - 1 day = Jan 4; next occurrence of day 5 in Jan = Jan 5
    assert result == date(2025, 1, 5)


@pytest.mark.django_db
def test_compute_next_due_monthly_day_31_in_feb():
    """Monthly template with day_of_period=31 after January → clamps to last day of Feb."""
    template = _make_template(
        frequency="monthly",
        day_of_period=31,
        start_date=date(2025, 1, 1),
        last_generated_date=date(2025, 1, 31),
    )
    result = compute_next_due_date(template=template)
    # February 2025 has 28 days → clamps to Feb 28
    assert result == date(2025, 2, 28)


@pytest.mark.django_db
def test_compute_next_due_weekly_basic():
    """Weekly template with day_of_period=1 (Monday) after a Wednesday should
    return the following Monday."""
    # 2025-01-08 is a Wednesday
    template = _make_template(
        frequency="weekly",
        day_of_period=1,  # Monday
        start_date=date(2025, 1, 1),
        last_generated_date=date(2025, 1, 8),  # Wednesday
    )
    result = compute_next_due_date(template=template)
    # Next Monday after Wednesday Jan 8 → Jan 13
    assert result == date(2025, 1, 13)


@pytest.mark.django_db
def test_compute_next_due_inactive_returns_none():
    """Inactive template always returns None regardless of dates."""
    template = _make_template(
        is_active=False,
        frequency="monthly",
        day_of_period=5,
        start_date=date(2025, 1, 1),
    )
    assert compute_next_due_date(template=template) is None


@pytest.mark.django_db
def test_compute_next_due_past_end_date_returns_none():
    """next_due beyond end_date returns None."""
    template = _make_template(
        frequency="monthly",
        day_of_period=5,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 4),   # end_date before day_of_period=5
        last_generated_date=None,
    )
    # start_date - 1 = Dec 31 2024; next occurrence = Jan 5 2025, which is > end_date Jan 4
    assert compute_next_due_date(template=template) is None


# ---------------------------------------------------------------------------
# materialize_template_for_date tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_materialize_creates_transaction():
    """Happy path: materializing a due date creates a Transaction and updates
    last_generated_date. Template uses USD = user's default currency so no FX
    rate lookup is required."""
    CurrencyFactory(code="USD")
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")
    template = _make_template(
        user=user, account=account, currency_code="USD", start_date=date(2025, 1, 5)
    )

    target = date(2025, 1, 5)
    txn = materialize_template_for_date(template=template, target_date=target)

    assert txn is not None
    assert Transaction.objects.filter(pk=txn.pk).exists()
    template.refresh_from_db()
    assert template.last_generated_date == target


@pytest.mark.django_db
def test_materialize_idempotent():
    """Calling materialize twice for the same date returns None on the second
    call and creates only one Transaction."""
    CurrencyFactory(code="USD")
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")
    template = _make_template(
        user=user, account=account, currency_code="USD", start_date=date(2025, 1, 5)
    )

    target = date(2025, 1, 5)
    first = materialize_template_for_date(template=template, target_date=target)
    second = materialize_template_for_date(template=template, target_date=target)

    assert first is not None
    assert second is None
    assert Transaction.objects.filter(description=template.description, user=user).count() == 1


@pytest.mark.django_db
def test_materialize_skips_inactive():
    """Inactive template → materialize returns None without creating a Transaction."""
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")
    template = _make_template(
        user=user, account=account, currency_code="USD",
        is_active=False, start_date=date(2025, 1, 5),
    )

    result = materialize_template_for_date(template=template, target_date=date(2025, 1, 5))

    assert result is None
    assert not Transaction.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_materialize_skips_before_start_date():
    """target_date before start_date → returns None, no Transaction created."""
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")
    template = _make_template(
        user=user, account=account, currency_code="USD", start_date=date(2025, 3, 1)
    )

    result = materialize_template_for_date(
        template=template, target_date=date(2025, 2, 1)
    )

    assert result is None
    assert not Transaction.objects.filter(user=user).exists()


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_materialize_task_happy_path():
    """Task materializes 2 active templates whose next due date is today.
    Templates use USD = user's default currency to avoid FX lookups."""
    CurrencyFactory(code="USD")
    today = date.today()
    user = UserFactory()

    for _ in range(2):
        account = AccountFactory(user=user, currency_code="USD")
        # day_of_period matches today's day so it falls due today
        _make_template(
            user=user,
            account=account,
            currency_code="USD",
            frequency="monthly",
            day_of_period=today.day,
            start_date=today,
            last_generated_date=None,
        )

    result = materialize_due_recurring_transactions(
        target_date_iso=today.isoformat()
    )

    assert result["materialized"] == 2
    assert Transaction.objects.filter(user=user).count() == 2


@pytest.mark.django_db
def test_materialize_task_skips_already_generated():
    """Template with last_generated_date=today is skipped (idempotency)."""
    today = date.today()
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")

    _make_template(
        user=user,
        account=account,
        currency_code="USD",
        frequency="monthly",
        day_of_period=today.day,
        start_date=today,
        last_generated_date=today,  # already generated
    )

    result = materialize_due_recurring_transactions(
        target_date_iso=today.isoformat()
    )

    assert result["skipped"] >= 1
    assert Transaction.objects.filter(user=user).count() == 0


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_recurring_template_view(client):
    """POST /api/v1/recurring/ → 201 with the created template data.
    Uses USD currency (matches user.default_currency_code) so no FX rate needed."""
    CurrencyFactory(code="USD")
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")

    payload = {
        "type": "expense",
        "amount": "250.00000000",
        "currency_code": "USD",
        "account_id": account.pk,
        "description": "Monthly rent",
        "frequency": "monthly",
        "day_of_period": 1,
        "start_date": "2025-01-01",
    }

    response = client.post(
        "/api/v1/recurring/",
        data=payload,
        content_type="application/json",
        **_auth_header(user),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Monthly rent"
    assert data["frequency"] == "monthly"
    assert RecurringTemplate.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_list_recurring_templates_view(client):
    """GET /api/v1/recurring/ returns only the authenticated user's templates."""
    user = UserFactory()
    other_user = UserFactory()

    account = AccountFactory(user=user, currency_code="USD")
    other_account = AccountFactory(user=other_user, currency_code="USD")

    _make_template(user=user, account=account)
    _make_template(user=user, account=account, description="Second template")
    _make_template(user=other_user, account=other_account, description="Other user")

    response = client.get(
        "/api/v1/recurring/",
        **_auth_header(user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    descriptions = {r["description"] for r in data["results"]}
    assert "Other user" not in descriptions


@pytest.mark.django_db
def test_recurring_template_ownership(client):
    """GET /api/v1/recurring/{pk}/ for another user's template → 404."""
    user = UserFactory()
    other_user = UserFactory()
    other_account = AccountFactory(user=other_user, currency_code="USD")

    other_template = _make_template(user=other_user, account=other_account)

    response = client.get(
        f"/api/v1/recurring/{other_template.pk}/",
        **_auth_header(user),
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_materialize_now_view(client):
    """POST /api/v1/recurring/{pk}/materialize-now/ with a due-today template
    → 201 and a Transaction is created. Uses USD to avoid FX rate lookup."""
    CurrencyFactory(code="USD")
    today = date.today()
    user = UserFactory()
    account = AccountFactory(user=user, currency_code="USD")

    template = _make_template(
        user=user,
        account=account,
        currency_code="USD",
        frequency="monthly",
        day_of_period=today.day,
        start_date=today,
        last_generated_date=None,
    )

    response = client.post(
        f"/api/v1/recurring/{template.pk}/materialize-now/",
        **_auth_header(user),
    )

    assert response.status_code == 201
    assert Transaction.objects.filter(user=user).count() == 1
