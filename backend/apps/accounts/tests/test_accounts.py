"""Tests for apps/accounts — models, services, selectors, and views."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Account
from apps.accounts.selectors import get_account_list_with_balance, get_account_with_balance
from apps.accounts.services import (
    create_account,
    reassign_transactions,
    soft_delete_account,
    update_account,
)
from apps.accounts.tests.factories import AccountFactory
from apps.currencies.tests.factories import CurrencyFactory
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory
from common.exceptions import (
    AccountCurrencyLockedError,
    AccountInUseError,
    AccountNotFoundError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def usd(db):
    return CurrencyFactory(code="USD", name="US Dollar", symbol="$", decimal_places=2)


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.user = user
    return client


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_account_user_name_unique_alive():
    """Two alive accounts with the same user+name violate the constraint;
    after soft-deleting the first, a new one with the same name succeeds."""
    user = UserFactory()
    AccountFactory(user=user, name="Wallet")

    with pytest.raises(IntegrityError):
        # direct ORM create bypasses factory sequence, triggers the constraint
        Account.objects.create(
            user=user,
            name="Wallet",
            account_type="cash",
            currency_code="USD",
        )


@pytest.mark.django_db
def test_account_user_name_unique_after_soft_delete():
    """After soft-deleting the first account the same name is reusable."""
    user = UserFactory()
    acc = AccountFactory(user=user, name="Wallet")
    acc.soft_delete()

    # Should not raise
    new_acc = Account.objects.create(
        user=user,
        name="Wallet",
        account_type="cash",
        currency_code="USD",
    )
    assert new_acc.pk is not None


@pytest.mark.django_db
def test_account_str():
    """__str__ returns '<name> (<currency_code>)'."""
    acc = AccountFactory(name="Main Checking", currency_code="EUR")
    assert str(acc) == "Main Checking (EUR)"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_account_valid(user, usd):
    acc = create_account(
        user=user,
        name="Savings Pot",
        account_type="savings",
        currency_code="USD",
        opening_balance=Decimal("500.00"),
    )
    assert acc.pk is not None
    assert acc.name == "Savings Pot"
    assert acc.account_type == "savings"
    assert acc.currency_code == "USD"
    assert acc.opening_balance == Decimal("500.00")
    assert acc.user == user


@pytest.mark.django_db
def test_create_account_unknown_currency_raises(user):
    """create_account raises ValueError for an unrecognised currency code."""
    with pytest.raises(ValueError, match="Unknown currency code"):
        create_account(
            user=user,
            name="Ghost Account",
            account_type="bank",
            currency_code="XYZ",
        )


@pytest.mark.django_db
def test_update_account_basic_fields(user, usd):
    acc = AccountFactory(user=user, name="Old Name", is_active=True)
    updated = update_account(account=acc, name="New Name", is_active=False)
    assert updated.name == "New Name"
    assert updated.is_active is False


@pytest.mark.django_db
def test_update_account_currency_locked_when_transactions_exist(user, usd):
    """Changing currency_code when transactions exist raises AccountCurrencyLockedError."""
    acc = AccountFactory(user=user, currency_code="USD")
    TransactionFactory(user=user, account=acc, currency_code="USD")

    with pytest.raises(AccountCurrencyLockedError):
        update_account(account=acc, currency_code="EUR")


@pytest.mark.django_db
def test_soft_delete_account_no_transactions(user):
    acc = AccountFactory(user=user)
    soft_delete_account(account=acc)
    acc.refresh_from_db()
    assert acc.deleted_at is not None


@pytest.mark.django_db
def test_soft_delete_account_with_transactions_raises(user, usd):
    """soft_delete_account raises AccountInUseError when transactions exist."""
    acc = AccountFactory(user=user, currency_code="USD")
    TransactionFactory(user=user, account=acc)

    with pytest.raises(AccountInUseError):
        soft_delete_account(account=acc)


@pytest.mark.django_db
def test_reassign_transactions(user, usd):
    """reassign_transactions moves all transactions from source to target and returns count."""
    source = AccountFactory(user=user, currency_code="USD")
    target = AccountFactory(user=user, currency_code="USD")

    TransactionFactory(user=user, account=source)
    TransactionFactory(user=user, account=source)

    count = reassign_transactions(source_account=source, target_account=target)

    assert count == 2
    assert target.transactions.count() == 2
    assert source.transactions.count() == 0


# ---------------------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_account_list_balance_correct(user, usd):
    """current_balance = opening_balance + income - expense."""
    acc = AccountFactory(user=user, currency_code="USD", opening_balance=Decimal("1000"))
    TransactionFactory(user=user, account=acc, type="income", amount=Decimal("200"))
    TransactionFactory(user=user, account=acc, type="expense", amount=Decimal("50"))

    qs = get_account_list_with_balance(user=user)
    annotated = qs.get(pk=acc.pk)

    assert annotated.current_balance == Decimal("1150")


@pytest.mark.django_db
def test_get_account_list_no_transactions(user):
    """current_balance equals opening_balance when there are no transactions."""
    acc = AccountFactory(user=user, opening_balance=Decimal("333"))

    qs = get_account_list_with_balance(user=user)
    annotated = qs.get(pk=acc.pk)

    assert annotated.current_balance == Decimal("333")


@pytest.mark.django_db
def test_get_account_list_archived_filter(user):
    """Inactive accounts are hidden by default; visible when include_archived=True."""
    active_acc = AccountFactory(user=user, is_active=True)
    inactive_acc = AccountFactory(user=user, is_active=False)

    default_ids = set(
        get_account_list_with_balance(user=user).values_list("pk", flat=True)
    )
    assert active_acc.pk in default_ids
    assert inactive_acc.pk not in default_ids

    all_ids = set(
        get_account_list_with_balance(user=user, filters={"include_archived": True})
        .values_list("pk", flat=True)
    )
    assert active_acc.pk in all_ids
    assert inactive_acc.pk in all_ids


@pytest.mark.django_db
def test_get_account_with_balance_not_found(user):
    """AccountNotFoundError is raised when the account belongs to a different user."""
    other_user = UserFactory()
    acc = AccountFactory(user=other_user)

    with pytest.raises(AccountNotFoundError):
        get_account_with_balance(account_id=acc.pk, user=user)


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_account_view(auth_client, usd):
    resp = auth_client.post(
        "/api/v1/accounts/",
        {
            "name": "Holiday Fund",
            "account_type": "savings",
            "currency_code": "USD",
            "opening_balance": "250.00",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Holiday Fund"
    assert data["account_type"] == "savings"
    assert data["currency_code"] == "USD"
    assert Decimal(data["opening_balance"]) == Decimal("250.00")


@pytest.mark.django_db
def test_list_accounts_view(auth_client, usd):
    """GET /accounts/ returns paginated results containing only the requesting user's accounts."""
    AccountFactory(user=auth_client.user, currency_code="USD")
    AccountFactory(user=auth_client.user, currency_code="USD")
    other_user = UserFactory()
    AccountFactory(user=other_user, currency_code="USD")

    resp = auth_client.get("/api/v1/accounts/")
    assert resp.status_code == 200

    data = resp.json()
    # DRF PageNumberPagination wraps results in a dict with 'results' key
    results = data.get("results", data)
    assert len(results) == 2


@pytest.mark.django_db
def test_detail_account_ownership(auth_client):
    """GET /accounts/{pk}/ for another user's account returns 404."""
    other_user = UserFactory()
    other_acc = AccountFactory(user=other_user)

    resp = auth_client.get(f"/api/v1/accounts/{other_acc.pk}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_summary_view(auth_client, usd):
    """GET /accounts/summary/ returns base_currency, total_assets, and by_account_type."""
    AccountFactory(
        user=auth_client.user,
        account_type="bank",
        currency_code="USD",
        opening_balance=Decimal("1000"),
    )

    resp = auth_client.get("/api/v1/accounts/summary/")
    assert resp.status_code == 200

    data = resp.json()
    assert "base_currency" in data
    assert "total_assets" in data
    assert "by_account_type" in data
    assert isinstance(data["by_account_type"], list)


@pytest.mark.django_db
def test_delete_account_with_transactions_returns_409(auth_client, usd):
    """DELETE /accounts/{pk}/ with linked transactions returns 409 Conflict."""
    acc = AccountFactory(user=auth_client.user, currency_code="USD")
    TransactionFactory(user=auth_client.user, account=acc)

    resp = auth_client.delete(f"/api/v1/accounts/{acc.pk}/")
    assert resp.status_code == 409
