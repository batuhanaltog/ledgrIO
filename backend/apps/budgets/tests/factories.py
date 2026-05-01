import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from apps.budgets.models import Budget
from apps.users.tests.factories import UserFactory
from apps.transactions.tests.factories import CategoryFactory


class BudgetFactory(DjangoModelFactory):
    class Meta:
        model = Budget

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    amount_limit = Decimal("500.00")
    period = Budget.Period.MONTHLY
    alert_at_50 = True
    alert_at_80 = True
    alert_at_100 = True
    is_active = True
