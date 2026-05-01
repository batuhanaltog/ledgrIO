from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.currencies.tests.factories import CurrencyFactory
from apps.transactions.models import Transaction
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    u = UserFactory()
    u.default_currency_code = "USD"
    u.save()
    return u


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.user = user
    return client


@pytest.fixture(autouse=True)
def usd_currency(db):
    return CurrencyFactory(code="USD")


@pytest.mark.django_db
def test_create_transaction(auth_client):
    resp = auth_client.post(
        "/api/v1/transactions/",
        {"type": "expense", "amount": "50.00", "currency_code": "USD", "date": str(date.today()), "description": "Test"},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "expense"
    assert Decimal(data["fx_rate_snapshot"]) == Decimal("1")
    assert data["base_currency"] == "USD"


@pytest.mark.django_db
def test_list_transactions(auth_client):
    TransactionFactory(user=auth_client.user)
    TransactionFactory(user=auth_client.user)
    other = UserFactory()
    TransactionFactory(user=other)

    resp = auth_client.get("/api/v1/transactions/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


@pytest.mark.django_db
def test_filter_by_type(auth_client):
    TransactionFactory(user=auth_client.user, type="expense")
    TransactionFactory(user=auth_client.user, type="income")

    resp = auth_client.get("/api/v1/transactions/?type=expense")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["type"] == "expense"


@pytest.mark.django_db
def test_filter_by_search(auth_client):
    TransactionFactory(user=auth_client.user, description="weekly groceries")
    TransactionFactory(user=auth_client.user, description="netflix")

    resp = auth_client.get("/api/v1/transactions/?search=groceries")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


@pytest.mark.django_db
def test_filter_by_amount_range(auth_client):
    TransactionFactory(user=auth_client.user, amount=Decimal("50.00"), amount_base=Decimal("50.00"))
    TransactionFactory(user=auth_client.user, amount=Decimal("200.00"), amount_base=Decimal("200.00"))

    resp = auth_client.get("/api/v1/transactions/?amount_min=100")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert Decimal(resp.json()["results"][0]["amount"]) == Decimal("200.00")


@pytest.mark.django_db
def test_get_transaction_detail(auth_client):
    tx = TransactionFactory(user=auth_client.user)
    resp = auth_client.get(f"/api/v1/transactions/{tx.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == tx.id


@pytest.mark.django_db
def test_get_other_user_transaction_returns_404(auth_client):
    other = UserFactory()
    tx = TransactionFactory(user=other)
    resp = auth_client.get(f"/api/v1/transactions/{tx.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_update_transaction(auth_client):
    tx = TransactionFactory(user=auth_client.user, description="old")
    resp = auth_client.patch(
        f"/api/v1/transactions/{tx.id}/",
        {"description": "new"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "new"


@pytest.mark.django_db
def test_delete_transaction(auth_client):
    tx = TransactionFactory(user=auth_client.user)
    resp = auth_client.delete(f"/api/v1/transactions/{tx.id}/")
    assert resp.status_code == 204
    assert Transaction.objects.filter(id=tx.id).count() == 0


@pytest.mark.django_db
def test_summary_endpoint(auth_client):
    today = date.today()
    TransactionFactory(user=auth_client.user, type="income", amount_base=Decimal("1000.00"), date=today)
    TransactionFactory(user=auth_client.user, type="expense", amount_base=Decimal("400.00"), date=today)

    resp = auth_client.get(f"/api/v1/transactions/summary/?date_from={today}&date_to={today}&group_by=month")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_income"]) == Decimal("1000.00000000")
    assert Decimal(data["total_expense"]) == Decimal("400.00000000")
    assert Decimal(data["net"]) == Decimal("600.00000000")
    assert len(data["running_balance"]) == 1


@pytest.mark.django_db
def test_unauthenticated_rejected(db):
    client = APIClient()
    resp = client.get("/api/v1/transactions/")
    assert resp.status_code == 401
