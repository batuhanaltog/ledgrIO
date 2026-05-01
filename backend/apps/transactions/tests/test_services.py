from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.categories.tests.factories import SystemCategoryFactory
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory
from apps.transactions.models import Transaction
from apps.transactions.services import (
    create_transaction,
    soft_delete_transaction,
    update_transaction,
)
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory
from common.exceptions import TransactionNotFoundError


@pytest.mark.django_db
def test_transaction_model_exists():
    fields = {f.name for f in Transaction._meta.get_fields()}
    assert "amount" in fields
    assert "amount_base" in fields
    assert "fx_rate_snapshot" in fields
    assert "currency_code" in fields
    assert "type" in fields
    assert "category" in fields
    assert "deleted_at" in fields


@pytest.mark.django_db
def test_create_transaction_same_currency(db):
    """When currency equals user default, fx_rate_snapshot=1 and amount_base=amount."""
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")

    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("50.00"),
        currency_code="USD",
        category_id=None,
        date=date.today(),
        description="Test",
        reference="",
    )

    assert tx.amount == Decimal("50.00")
    assert tx.fx_rate_snapshot == Decimal("1")
    assert tx.amount_base == Decimal("50.00")
    assert tx.base_currency == "USD"


@pytest.mark.django_db
def test_create_transaction_foreign_currency_snapshots_rate(db):
    """FX snapshot is stored; amount_base is amount * rate."""
    user = UserFactory()
    user.default_currency_code = "TRY"
    user.save()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33.00000000"), rate_date=date.today())

    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("10.00000000"),
        currency_code="USD",
        category_id=None,
        date=date.today(),
        description="",
        reference="",
    )

    assert tx.fx_rate_snapshot == Decimal("33.00000000")
    assert tx.amount_base == Decimal("330.00000000")


@pytest.mark.django_db
def test_create_transaction_with_category(db):
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    system_cat = SystemCategoryFactory()

    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("20.00"),
        currency_code="USD",
        category_id=system_cat.id,
        date=date.today(),
        description="",
        reference="",
    )
    assert tx.category_id == system_cat.id


@pytest.mark.django_db
def test_update_transaction_amount_recalculates_fx(db):
    """Updating amount triggers FX recalculation."""
    user = UserFactory()
    user.default_currency_code = "TRY"
    user.save()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33.00000000"), rate_date=date.today())

    tx = TransactionFactory(
        user=user,
        currency_code="USD",
        base_currency="TRY",
        amount=Decimal("10.00000000"),
        amount_base=Decimal("330.00000000"),
        fx_rate_snapshot=Decimal("33.00000000"),
    )

    updated = update_transaction(transaction=tx, user=user, amount=Decimal("20.00000000"))
    assert updated.amount_base == Decimal("660.00000000")
    assert updated.fx_rate_snapshot == Decimal("33.00000000")


@pytest.mark.django_db
def test_update_transaction_description_preserves_fx(db):
    """Updating non-monetary fields preserves the FX snapshot."""
    user = UserFactory()
    tx = TransactionFactory(
        user=user,
        fx_rate_snapshot=Decimal("33.00000000"),
        amount_base=Decimal("330.00000000"),
    )

    updated = update_transaction(transaction=tx, user=user, description="New description")
    assert updated.fx_rate_snapshot == Decimal("33.00000000")
    assert updated.amount_base == Decimal("330.00000000")
    assert updated.description == "New description"


@pytest.mark.django_db
def test_soft_delete_transaction(db):
    user = UserFactory()
    tx = TransactionFactory(user=user)
    soft_delete_transaction(transaction=tx, user=user)
    tx.refresh_from_db()
    assert tx.deleted_at is not None
    assert Transaction.objects.filter(id=tx.id).count() == 0
    assert Transaction.all_objects.filter(id=tx.id).count() == 1


@pytest.mark.django_db
def test_soft_delete_other_user_transaction_raises(db):
    user = UserFactory()
    other = UserFactory()
    tx = TransactionFactory(user=other)
    with pytest.raises(TransactionNotFoundError):
        soft_delete_transaction(transaction=tx, user=user)
