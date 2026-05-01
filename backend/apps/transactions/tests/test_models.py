import pytest
from decimal import Decimal
from .factories import TransactionFactory, CategoryFactory


@pytest.mark.django_db
class TestTransactionModel:
    def test_create_transaction(self):
        tx = TransactionFactory()
        assert tx.pk is not None
        assert tx.fee == Decimal("0")

    def test_str(self):
        tx = TransactionFactory(transaction_type="EXPENSE", amount=Decimal("50"), currency="USD")
        assert "EXPENSE" in str(tx)
        assert "50" in str(tx)

    def test_category_str(self):
        cat = CategoryFactory(name="Food")
        assert str(cat) == "Food"
