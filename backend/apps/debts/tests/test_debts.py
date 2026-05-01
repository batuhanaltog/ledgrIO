"""Tests for apps/debts — models, services, selectors, and views."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import AccountFactory
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory
from apps.debts.models import Debt, DebtCategory, DebtPayment
from apps.debts.selectors import get_debt_monthly_summary
from apps.debts.services import (
    create_debt,
    create_debt_category,
    record_debt_payment,
    reverse_debt_payment,
    soft_delete_debt,
    soft_delete_debt_category,
    update_debt,
    update_debt_category,
)
from apps.users.tests.factories import UserFactory
from common.exceptions import (
    DebtBalanceUnderflowError,
    DebtCategoryCycleError,
    DebtCategoryHasChildrenError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_client(user) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _make_usd_debt(user, *, original_amount: Decimal = Decimal("1000")) -> Debt:
    """Create a USD debt for *user*, seeding Currency if necessary."""
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")  # noqa: F841  (keep ref alive)
    return create_debt(
        user=user,
        category_id=None,
        name="Test Debt",
        original_amount=original_amount,
        expected_monthly_payment=Decimal("100"),
        currency_code="USD",
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_debt_check_constraint_negative_original_amount():
    """DB check constraint rejects negative original_amount."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    with pytest.raises(IntegrityError):
        Debt.objects.create(
            user=user,
            name="Bad Debt",
            original_amount=Decimal("-1"),
            current_balance=Decimal("0"),
            expected_monthly_payment=Decimal("100"),
            currency_code="USD",
        )


@pytest.mark.django_db
def test_debt_str():
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user)
    assert str(debt) == "Test Debt (USD)"


@pytest.mark.django_db
def test_debt_category_str():
    user = UserFactory()
    cat = DebtCategory.objects.create(user=user, name="Housing")
    assert str(cat) == "Housing"


# ---------------------------------------------------------------------------
# DebtCategory service tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_debt_category_basic():
    user = UserFactory()
    cat = create_debt_category(user=user, name="Credit Cards")
    assert cat.pk is not None
    assert cat.name == "Credit Cards"
    assert cat.parent is None
    assert cat.user == user


@pytest.mark.django_db
def test_create_debt_category_with_parent():
    user = UserFactory()
    parent = create_debt_category(user=user, name="Loans")
    child = create_debt_category(user=user, name="Car Loan", parent_id=parent.pk)
    assert child.parent_id == parent.pk


@pytest.mark.django_db
def test_soft_delete_category_with_children_raises():
    user = UserFactory()
    parent = create_debt_category(user=user, name="Loans")
    create_debt_category(user=user, name="Car Loan", parent_id=parent.pk)
    with pytest.raises(DebtCategoryHasChildrenError):
        soft_delete_debt_category(category=parent)


@pytest.mark.django_db
def test_cycle_detection_on_update():
    """Making a category its own ancestor must raise DebtCategoryCycleError."""
    user = UserFactory()
    a = create_debt_category(user=user, name="A")
    b = create_debt_category(user=user, name="B", parent_id=a.pk)
    c = create_debt_category(user=user, name="C", parent_id=b.pk)
    with pytest.raises(DebtCategoryCycleError):
        update_debt_category(category=a, parent_id=c.pk)


# ---------------------------------------------------------------------------
# Debt service tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_debt_sets_current_balance_to_original():
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = create_debt(
        user=user,
        category_id=None,
        name="Mortgage",
        original_amount=Decimal("200000"),
        expected_monthly_payment=Decimal("1500"),
        currency_code="USD",
    )
    assert debt.current_balance == Decimal("200000")
    assert debt.original_amount == Decimal("200000")


@pytest.mark.django_db
def test_update_debt_cannot_change_current_balance_directly():
    """update_debt strips current_balance; the value should remain unchanged."""
    user = UserFactory()
    debt = _make_usd_debt(user, original_amount=Decimal("500"))
    original_balance = debt.current_balance

    updated = update_debt(debt=debt, current_balance=Decimal("1"))
    updated.refresh_from_db()
    assert updated.current_balance == original_balance


@pytest.mark.django_db
def test_soft_delete_debt_with_payments_raises():
    """Debt that has payment records cannot be soft-deleted."""
    from rest_framework.exceptions import ValidationError as DRFValidationError

    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("500"))
    account = AccountFactory(user=user, currency_code="USD")

    record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("100"),
        paid_at=date.today(),
        user=user,
    )
    debt.refresh_from_db()

    with pytest.raises(DRFValidationError):
        soft_delete_debt(debt=debt)


@pytest.mark.django_db
def test_soft_delete_debt_no_payments_succeeds():
    user = UserFactory()
    debt = _make_usd_debt(user)
    soft_delete_debt(debt=debt)
    debt.refresh_from_db()
    assert debt.deleted_at is not None


# ---------------------------------------------------------------------------
# record_debt_payment service tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_record_debt_payment_same_currency():
    """Happy path: Transaction + DebtPayment created, balance decremented."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("1000"))
    account = AccountFactory(user=user, currency_code="USD")

    payment = record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("200"),
        paid_at=date(2026, 5, 1),
        user=user,
    )

    debt.refresh_from_db()
    assert debt.current_balance == Decimal("800")
    assert payment.amount == Decimal("200")
    assert payment.transaction is not None
    assert DebtPayment.objects.filter(pk=payment.pk).exists()


@pytest.mark.django_db
def test_record_debt_payment_settles_debt_on_zero():
    """Full payment sets is_settled=True."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("500"))
    account = AccountFactory(user=user, currency_code="USD")

    record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("500"),
        paid_at=date(2026, 5, 1),
        user=user,
    )

    debt.refresh_from_db()
    assert debt.current_balance == Decimal("0")
    assert debt.is_settled is True


@pytest.mark.django_db
def test_record_debt_payment_balance_underflow_raises():
    """Payment amount exceeding current_balance raises DebtBalanceUnderflowError."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("100"))
    account = AccountFactory(user=user, currency_code="USD")

    with pytest.raises(DebtBalanceUnderflowError):
        record_debt_payment(
            debt=debt,
            account=account,
            amount=Decimal("101"),
            paid_at=date(2026, 5, 1),
            user=user,
        )


@pytest.mark.django_db
def test_record_debt_payment_atomicity():
    """If DebtPayment creation fails, the Transaction should also be rolled back."""
    from unittest.mock import patch

    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("500"))
    account = AccountFactory(user=user, currency_code="USD")

    from apps.transactions.models import Transaction

    tx_count_before = Transaction.objects.count()
    payment_count_before = DebtPayment.objects.count()

    with patch("apps.debts.services.DebtPayment.objects.create", side_effect=RuntimeError("boom")), pytest.raises(RuntimeError):
            record_debt_payment(
                debt=debt,
                account=account,
                amount=Decimal("100"),
                paid_at=date(2026, 5, 1),
                user=user,
            )

    # Transaction should have been rolled back due to @transaction.atomic
    assert Transaction.objects.count() == tx_count_before
    assert DebtPayment.objects.count() == payment_count_before

    # Debt balance should be unchanged
    debt.refresh_from_db()
    assert debt.current_balance == Decimal("500")


@pytest.mark.django_db
def test_record_debt_payment_cross_currency():
    """USD debt paid from TRY account: Transaction in TRY, DebtPayment in USD."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY", name="Turkish Lira", symbol="₺", decimal_places=2)
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33"), rate_date=date(2026, 5, 1))

    # debt is in USD; account is in TRY
    debt = create_debt(
        user=user,
        category_id=None,
        name="USD Debt",
        original_amount=Decimal("100"),
        expected_monthly_payment=Decimal("10"),
        currency_code="USD",
    )
    account = AccountFactory(user=user, currency_code="TRY")

    # Pay 3300 TRY (= $100 at rate 33)
    payment = record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("100"),  # in debt currency (USD)
        paid_at=date(2026, 5, 1),
        user=user,
    )

    debt.refresh_from_db()
    # Debt balance should drop by $100
    assert debt.current_balance == Decimal("0")
    assert debt.is_settled is True

    # DebtPayment stores USD amount
    assert payment.amount == Decimal("100")

    # Transaction stores TRY amount (100 USD * 33 = 3300 TRY)
    payment.transaction.refresh_from_db()
    assert payment.transaction.currency_code == "TRY"
    assert payment.transaction.amount == Decimal("3300.00000000")


# ---------------------------------------------------------------------------
# reverse_debt_payment service tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_reverse_debt_payment_restores_balance():
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("1000"))
    account = AccountFactory(user=user, currency_code="USD")

    payment = record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("300"),
        paid_at=date(2026, 5, 1),
        user=user,
    )
    debt.refresh_from_db()
    assert debt.current_balance == Decimal("700")

    reverse_debt_payment(payment=payment)

    debt.refresh_from_db()
    assert debt.current_balance == Decimal("1000")


@pytest.mark.django_db
def test_reverse_debt_payment_unsets_is_settled():
    """Reversing the payment that settled a debt resets is_settled to False."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("500"))
    account = AccountFactory(user=user, currency_code="USD")

    payment = record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("500"),
        paid_at=date(2026, 5, 1),
        user=user,
    )
    debt.refresh_from_db()
    assert debt.is_settled is True

    reverse_debt_payment(payment=payment)

    debt.refresh_from_db()
    assert debt.is_settled is False
    assert debt.current_balance == Decimal("500")


@pytest.mark.django_db
def test_reverse_debt_payment_soft_deletes_transaction():
    """Reversing a payment soft-deletes the linked Transaction and removes the DebtPayment."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("500"))
    account = AccountFactory(user=user, currency_code="USD")

    payment = record_debt_payment(
        debt=debt,
        account=account,
        amount=Decimal("200"),
        paid_at=date(2026, 5, 1),
        user=user,
    )
    tx_pk = payment.transaction_id
    payment_pk = payment.pk

    reverse_debt_payment(payment=payment)

    # Payment record should be hard-deleted
    assert not DebtPayment.objects.filter(pk=payment_pk).exists()

    # Transaction should be soft-deleted (deleted_at set)
    from apps.transactions.models import Transaction

    tx = Transaction.all_objects.get(pk=tx_pk)
    assert tx.deleted_at is not None


# ---------------------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_debt_monthly_summary_arithmetic():
    """expected_total, paid_total, remaining_total are arithmetically correct."""
    user = UserFactory()
    CurrencyFactory(code="USD")

    # Two unsettled debts with different expected payments
    debt_a = create_debt(
        user=user,
        category_id=None,
        name="Debt A",
        original_amount=Decimal("5000"),
        expected_monthly_payment=Decimal("400"),
        currency_code="USD",
    )
    create_debt(
        user=user,
        category_id=None,
        name="Debt B",
        original_amount=Decimal("2000"),
        expected_monthly_payment=Decimal("200"),
        currency_code="USD",
    )

    # Pay debt_a partially in May 2026
    account = AccountFactory(user=user, currency_code="USD")
    record_debt_payment(
        debt=debt_a,
        account=account,
        amount=Decimal("300"),
        paid_at=date(2026, 5, 15),
        user=user,
    )

    summary = get_debt_monthly_summary(user=user, year=2026, month=5)

    assert summary["expected_total"] == Decimal("600")  # 400 + 200
    assert summary["paid_total"] == Decimal("300")
    assert summary["remaining_total"] == Decimal("300")


@pytest.mark.django_db
def test_get_debt_monthly_summary_query_count():
    """Monthly summary must not issue more than 3 DB queries."""
    user = UserFactory()
    CurrencyFactory(code="USD")
    create_debt(
        user=user,
        category_id=None,
        name="Debt X",
        original_amount=Decimal("1000"),
        expected_monthly_payment=Decimal("100"),
        currency_code="USD",
    )

    with CaptureQueriesContext(connection) as ctx:
        get_debt_monthly_summary(user=user, year=2026, month=5)

    assert len(ctx.captured_queries) <= 3, (
        f"Expected ≤3 queries but got {len(ctx.captured_queries)}"
    )


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_debts_view_returns_only_user_debts():
    user = UserFactory()
    other = UserFactory()
    CurrencyFactory(code="USD")

    _make_usd_debt(user)
    _make_usd_debt(other)

    client = _auth_client(user)
    response = client.get("/api/v1/debts/")

    assert response.status_code == 200
    # Paginated response
    ids = [d["id"] for d in response.data["results"]]
    user_debt_ids = list(Debt.objects.filter(user=user).values_list("pk", flat=True))
    other_debt_ids = list(Debt.objects.filter(user=other).values_list("pk", flat=True))
    for did in user_debt_ids:
        assert did in ids
    for did in other_debt_ids:
        assert did not in ids


@pytest.mark.django_db
def test_create_debt_view():
    user = UserFactory()
    CurrencyFactory(code="USD")

    client = _auth_client(user)
    payload = {
        "name": "Car Loan",
        "original_amount": "15000.00",
        "expected_monthly_payment": "400.00",
        "currency_code": "USD",
    }
    response = client.post("/api/v1/debts/", data=payload, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "Car Loan"
    assert Decimal(response.data["current_balance"]) == Decimal("15000")


@pytest.mark.django_db
def test_debt_ownership_returns_404_for_other_user_debt():
    user = UserFactory()
    other = UserFactory()
    CurrencyFactory(code="USD")

    other_debt = _make_usd_debt(other)

    client = _auth_client(user)
    response = client.get(f"/api/v1/debts/{other_debt.pk}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_debt_payment_view_creates_payment_and_updates_balance():
    user = UserFactory()
    CurrencyFactory(code="USD")
    debt = _make_usd_debt(user, original_amount=Decimal("1000"))
    account = AccountFactory(user=user, currency_code="USD")

    client = _auth_client(user)
    payload = {
        "account_id": account.pk,
        "amount": "250.00",
        "paid_at": "2026-05-01",
    }
    response = client.post(f"/api/v1/debts/{debt.pk}/payments/", data=payload, format="json")

    assert response.status_code == 201
    assert Decimal(response.data["amount"]) == Decimal("250")

    debt.refresh_from_db()
    assert debt.current_balance == Decimal("750")
