"""Phase 4.5 end-to-end flow: Accounts + Debts + Recurring."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory


@pytest.fixture(autouse=True)
def _reset_ratelimit_cache() -> None:
    cache.clear()


@pytest.mark.django_db
def test_phase4_5_full_flow(db):
    """
    Full Phase 4.5 flow:
    register → set monthly_income → create 2 accounts
    → create recurring salary template (monthly, day=1)
    → create recurring rent template (monthly, day=5)
    → materialize May 1 salary + May 5 rent → verify 2 transactions
    → create DebtCategory + Debt
    → record payment → verify atomic write (Transaction + DebtPayment + balance)
    → GET monthly-summary → verify breakdown + leftover_after_expected_debts
    → DELETE (reverse) payment → verify balance restored
    → GET /accounts/summary/ → verify total_assets
    → DELETE account with linked tx → 409 CONFLICT
    """
    CurrencyFactory(code="TRY")
    today = date.today()

    client = APIClient()

    # Register
    resp = client.post(
        "/api/v1/auth/register/",
        {"email": "e2e45@ledgr.io", "password": "SuperSecure123!", "default_currency_code": "TRY"},
        format="json",
    )
    assert resp.status_code == 201

    # Login
    resp = client.post(
        "/api/v1/auth/login/",
        {"email": "e2e45@ledgr.io", "password": "SuperSecure123!"},
        format="json",
    )
    assert resp.status_code == 200
    access = resp.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # Set monthly_income on profile (nested under "profile" key)
    resp = client.patch(
        "/api/v1/users/me/",
        {"profile": {"monthly_income": "30000.00000000"}},
        format="json",
    )
    assert resp.status_code == 200

    # Create two accounts
    resp = client.post(
        "/api/v1/accounts/",
        {"name": "Maaş Hesabı", "account_type": "bank", "currency_code": "TRY", "opening_balance": "1000.00"},
        format="json",
    )
    assert resp.status_code == 201
    bank_account_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/accounts/",
        {"name": "Nakit Cüzdan", "account_type": "cash", "currency_code": "TRY"},
        format="json",
    )
    assert resp.status_code == 201
    cash_account_id = resp.json()["id"]

    # List accounts
    resp = client.get("/api/v1/accounts/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    # Create recurring salary template (income, monthly day=1)
    resp = client.post(
        "/api/v1/recurring/",
        {
            "type": "income",
            "amount": "30000.00",
            "currency_code": "TRY",
            "account_id": bank_account_id,
            "description": "Aylık maaş",
            "frequency": "monthly",
            "day_of_period": 1,
            "start_date": "2026-01-01",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.json()
    salary_template_id = resp.json()["id"]

    # Create recurring rent template (expense, monthly day=5)
    resp = client.post(
        "/api/v1/recurring/",
        {
            "type": "expense",
            "amount": "12000.00",
            "currency_code": "TRY",
            "account_id": bank_account_id,
            "description": "Aylık kira",
            "frequency": "monthly",
            "day_of_period": 5,
            "start_date": "2026-01-05",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.json()
    rent_template_id = resp.json()["id"]

    # Materialize salary (May 1)
    resp = client.post(f"/api/v1/recurring/{salary_template_id}/materialize-now/")
    assert resp.status_code in (200, 201), resp.json()

    # Materialize rent (May 5) — but since day_of_period=5 and today may differ,
    # materialize-now should work regardless
    resp = client.post(f"/api/v1/recurring/{rent_template_id}/materialize-now/")
    assert resp.status_code in (200, 201), resp.json()

    # Verify transactions created
    resp = client.get("/api/v1/transactions/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    # Create DebtCategory
    resp = client.post(
        "/api/v1/debts/categories/",
        {"name": "Garanti Bankası"},
        format="json",
    )
    assert resp.status_code == 201
    category_id = resp.json()["id"]

    # Create Debt
    resp = client.post(
        "/api/v1/debts/",
        {
            "name": "Kredi kartı asgari",
            "original_amount": "5000.00",
            "expected_monthly_payment": "500.00",
            "currency_code": "TRY",
            "category_id": category_id,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.json()
    debt_id = resp.json()["id"]
    assert Decimal(resp.json()["current_balance"]) == Decimal("5000.00")

    # Record payment
    resp = client.post(
        f"/api/v1/debts/{debt_id}/payments/",
        {"account_id": cash_account_id, "amount": "500.00", "paid_at": str(today)},
        format="json",
    )
    assert resp.status_code == 201, resp.json()
    payment_data = resp.json()
    payment_id = payment_data["id"]
    assert Decimal(payment_data["debt"]["current_balance"]) == Decimal("4500.00")
    assert payment_data["debt"]["is_settled"] is False

    # GET monthly summary
    resp = client.get(f"/api/v1/debts/monthly-summary/?year={today.year}&month={today.month}")
    assert resp.status_code == 200
    summary = resp.json()
    assert Decimal(summary["expected_total"]) == Decimal("500.00")
    assert Decimal(summary["paid_total"]) == Decimal("500.00")
    assert Decimal(summary["remaining_total"]) == Decimal("0.00")
    # monthly_income was set to 30000
    assert summary["monthly_income"] is not None
    assert summary["leftover_after_expected_debts"] is not None

    # Reverse payment
    resp = client.delete(f"/api/v1/debts/{debt_id}/payments/{payment_id}/")
    assert resp.status_code == 204, resp.json() if resp.content else "(no content)"

    # Verify balance restored
    resp = client.get(f"/api/v1/debts/{debt_id}/")
    assert resp.status_code == 200
    assert Decimal(resp.json()["current_balance"]) == Decimal("5000.00")

    # GET accounts summary
    resp = client.get("/api/v1/accounts/summary/")
    assert resp.status_code == 200
    summary = resp.json()
    assert "total_assets" in summary
    assert "base_currency" in summary
    assert summary["base_currency"] == "TRY"

    # DELETE account with linked transactions → 409
    resp = client.delete(f"/api/v1/accounts/{bank_account_id}/")
    assert resp.status_code == 409
