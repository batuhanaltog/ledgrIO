import pytest
from decimal import Decimal
from datetime import date
from apps.transactions.querysets import get_running_balance, get_transaction_summary
from .factories import TransactionFactory, UserFactory
from apps.transactions.models import Transaction


@pytest.mark.django_db
class TestRunningBalance:
    def test_running_balance_accumulates(self):
        user = UserFactory()
        TransactionFactory(user=user, transaction_type=Transaction.TransactionType.INCOME, amount=Decimal("1000"), transaction_date=date(2024, 1, 1))
        TransactionFactory(user=user, transaction_type=Transaction.TransactionType.EXPENSE, amount=Decimal("300"), transaction_date=date(2024, 1, 2))
        TransactionFactory(user=user, transaction_type=Transaction.TransactionType.INCOME, amount=Decimal("500"), transaction_date=date(2024, 1, 3))

        rows = get_running_balance(user.id)
        assert len(rows) == 3
        balances = [float(row["running_balance"]) for row in rows]
        assert balances[0] == 1000.0
        assert balances[1] == 700.0
        assert balances[2] == 1200.0

    def test_running_balance_empty_user(self):
        user = UserFactory()
        rows = get_running_balance(user.id)
        assert rows == []

    def test_running_balance_isolated_per_user(self):
        user1 = UserFactory()
        user2 = UserFactory()
        TransactionFactory(user=user1, transaction_type=Transaction.TransactionType.INCOME, amount=Decimal("500"), transaction_date=date(2024, 1, 1))
        TransactionFactory(user=user2, transaction_type=Transaction.TransactionType.INCOME, amount=Decimal("999"), transaction_date=date(2024, 1, 1))

        rows = get_running_balance(user1.id)
        assert len(rows) == 1
        assert float(rows[0]["running_balance"]) == 500.0


@pytest.mark.django_db
class TestTransactionSummary:
    def test_summary_groups_by_type(self):
        user = UserFactory()
        TransactionFactory.create_batch(3, user=user, transaction_type=Transaction.TransactionType.EXPENSE, amount=Decimal("100"), transaction_date=date(2024, 1, 15))
        TransactionFactory(user=user, transaction_type=Transaction.TransactionType.INCOME, amount=Decimal("500"), transaction_date=date(2024, 1, 15))

        rows = get_transaction_summary(user.id, "2024-01-01", "2024-01-31")
        types = [row["transaction_type"] for row in rows]
        assert "EXPENSE" in types
        assert "INCOME" in types

    def test_summary_respects_date_range(self):
        user = UserFactory()
        TransactionFactory(user=user, transaction_type=Transaction.TransactionType.EXPENSE, amount=Decimal("100"), transaction_date=date(2024, 1, 1))
        TransactionFactory(user=user, transaction_type=Transaction.TransactionType.EXPENSE, amount=Decimal("200"), transaction_date=date(2024, 3, 1))

        rows = get_transaction_summary(user.id, "2024-01-01", "2024-01-31")
        assert len(rows) == 1
        assert float(rows[0]["total_amount"]) == 100.0
