import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from django.utils import timezone
from apps.transactions.models import Transaction, Category
from apps.users.tests.factories import UserFactory
from apps.portfolios.tests.factories import PortfolioFactory


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    color = "#6366f1"
    is_income = False


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SubFactory(UserFactory)
    portfolio = factory.SubFactory(PortfolioFactory, user=factory.SelfAttribute("..user"))
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    transaction_type = Transaction.TransactionType.EXPENSE
    amount = Decimal("100.00000000")
    currency = "USD"
    transaction_date = factory.LazyFunction(lambda: timezone.now().date())
