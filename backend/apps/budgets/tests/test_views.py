from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import AccountFactory
from apps.budgets.models import Budget
from apps.budgets.tests.factories import BudgetFactory
from apps.currencies.tests.factories import CurrencyFactory
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory


def _auth_client(user) -> APIClient:
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# ---------------------------------------------------------------------------
# GET /api/v1/budgets/ — list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_list_happy_path():
    user = UserFactory()
    CurrencyFactory(code="USD")
    BudgetFactory(user=user, name="Food")
    BudgetFactory(user=user, name="Rent")

    response = _auth_client(user).get("/api/v1/budgets/")

    assert response.status_code == 200
    assert response.data["count"] == 2
    result = response.data["results"][0]
    assert "spent" in result
    assert "remaining" in result
    assert "usage_pct" in result


@pytest.mark.django_db
def test_budget_list_auth_guard():
    response = APIClient().get("/api/v1/budgets/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_budget_list_only_own_budgets():
    user = UserFactory()
    other = UserFactory()
    BudgetFactory(user=user)
    BudgetFactory(user=other)

    response = _auth_client(user).get("/api/v1/budgets/")

    assert response.data["count"] == 1


# ---------------------------------------------------------------------------
# POST /api/v1/budgets/ — create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_create_happy_path():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "Groceries",
        "amount": "500.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
    }, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "Groceries"
    assert response.data["spent"] == "0.00000000"
    assert Budget.objects.filter(user=user, name="Groceries").exists()


@pytest.mark.django_db
def test_budget_create_auth_guard():
    response = APIClient().post("/api/v1/budgets/", {
        "name": "X", "amount": "100", "date_from": "2026-05-01", "date_to": "2026-05-31"
    }, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_budget_create_invalid_dates():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "Bad",
        "amount": "100.00000000",
        "date_from": "2026-05-31",
        "date_to": "2026-05-01",
    }, format="json")

    assert response.status_code == 400
    assert response.data["error"]["type"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_budget_create_negative_amount_rejected():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "X",
        "amount": "-100.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
    }, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_budget_create_threshold_above_one_rejected():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "X",
        "amount": "500.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
        "alert_threshold": "1.50000000",
    }, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_budget_create_with_spent_returns_correct_usage():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")

    create_response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "Food",
        "amount": "1000.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
    }, format="json")
    assert create_response.status_code == 201
    budget_pk = create_response.data["id"]

    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("300.00000000"), amount_base=Decimal("300.00000000"),
        currency_code="USD", base_currency="USD", date=date(2026, 5, 10),
    )

    response = _auth_client(user).get(f"/api/v1/budgets/{budget_pk}/")

    assert response.status_code == 200
    assert Decimal(response.data["spent"]) == Decimal("300.00000000")
    assert Decimal(response.data["usage_pct"]) == Decimal("0.3")


# ---------------------------------------------------------------------------
# GET /api/v1/budgets/<pk>/ — detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_detail_ownership():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    response = _auth_client(user).get(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/budgets/<pk>/ — update
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_update_happy_path():
    user = UserFactory()
    budget = BudgetFactory(user=user, name="Old Name")

    response = _auth_client(user).patch(
        f"/api/v1/budgets/{budget.pk}/", {"name": "New Name"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "New Name"


@pytest.mark.django_db
def test_budget_update_ownership():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    response = _auth_client(user).patch(
        f"/api/v1/budgets/{budget.pk}/", {"name": "Hack"}, format="json"
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/budgets/<pk>/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_delete_happy_path():
    user = UserFactory()
    budget = BudgetFactory(user=user)

    response = _auth_client(user).delete(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 204
    assert not Budget.objects.filter(pk=budget.pk).exists()


@pytest.mark.django_db
def test_budget_delete_ownership():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    response = _auth_client(user).delete(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 404
    assert Budget.objects.filter(pk=budget.pk).exists()
