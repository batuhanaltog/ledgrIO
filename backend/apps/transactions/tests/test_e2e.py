from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory
from apps.transactions.models import Transaction


@pytest.fixture(autouse=True)
def _reset_ratelimit_cache() -> None:
    cache.clear()


@pytest.mark.django_db
def test_full_transaction_flow(db):
    """
    Full Phase 4 flow:
    register → login → create subcategory under system category
    → create expense (USD) → verify FX snapshot
    → create income (TRY) → verify rate=1
    → filter by category → search by description
    → get monthly summary → verify running balance
    → soft delete → verify not in list
    """
    # Setup currencies and FX rate
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    today = date.today()
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33.00000000"), rate_date=today)

    # Create a system category (simulating what seed migration provides)
    food = Category.objects.create(name="Food", is_system=True)

    # Register user with TRY as default currency
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/register/",
        {"email": "e2e@ledgr.io", "password": "SuperSecure123!", "default_currency_code": "TRY"},
        format="json",
    )
    assert resp.status_code == 201

    # Login
    resp = client.post(
        "/api/v1/auth/login/",
        {"email": "e2e@ledgr.io", "password": "SuperSecure123!"},
        format="json",
    )
    assert resp.status_code == 200
    access = resp.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # Create user subcategory under system category
    resp = client.post(
        "/api/v1/categories/",
        {"name": "Restaurant", "parent_id": food.id, "icon": "🍽️", "color": "#FF9800"},
        format="json",
    )
    assert resp.status_code == 201
    restaurant_id = resp.json()["id"]

    # Create expense in USD (user default is TRY → FX snapshot expected)
    resp = client.post(
        "/api/v1/transactions/",
        {
            "type": "expense",
            "amount": "10.00000000",
            "currency_code": "USD",
            "category_id": restaurant_id,
            "date": str(today),
            "description": "lunch at restaurant",
        },
        format="json",
    )
    assert resp.status_code == 201
    expense = resp.json()
    assert Decimal(expense["fx_rate_snapshot"]) == Decimal("33.00000000")
    assert Decimal(expense["amount_base"]) == Decimal("330.00000000")
    assert expense["base_currency"] == "TRY"
    expense_id = expense["id"]

    # Create income in TRY (same as default → rate=1)
    resp = client.post(
        "/api/v1/transactions/",
        {
            "type": "income",
            "amount": "5000.00000000",
            "currency_code": "TRY",
            "date": str(today),
            "description": "salary",
        },
        format="json",
    )
    assert resp.status_code == 201
    income = resp.json()
    assert Decimal(income["fx_rate_snapshot"]) == Decimal("1")
    assert Decimal(income["amount_base"]) == Decimal("5000.00000000")

    # Filter by category
    resp = client.get(f"/api/v1/transactions/?category={restaurant_id}")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    # Search by description
    resp = client.get("/api/v1/transactions/?search=lunch")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    # Monthly summary
    resp = client.get(f"/api/v1/transactions/summary/?date_from={today}&date_to={today}&group_by=month")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_income"]) == Decimal("5000.00000000")
    assert Decimal(data["total_expense"]) == Decimal("330.00000000")
    assert Decimal(data["net"]) == Decimal("4670.00000000")
    assert len(data["running_balance"]) == 1

    # Soft delete expense
    resp = client.delete(f"/api/v1/transactions/{expense_id}/")
    assert resp.status_code == 204

    # Verify not in list
    resp = client.get("/api/v1/transactions/")
    assert resp.status_code == 200
    ids = [tx["id"] for tx in resp.json()["results"]]
    assert expense_id not in ids

    # Verify still in DB via all_objects
    assert Transaction.all_objects.filter(id=expense_id).exists()
