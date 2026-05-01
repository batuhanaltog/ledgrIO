from __future__ import annotations

from datetime import date
from decimal import Decimal

import factory

from apps.budgets.models import Budget
from apps.users.tests.factories import UserFactory


class BudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Budget

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Budget {n}")
    category = None
    amount = Decimal("500.00000000")
    date_from = factory.LazyFunction(lambda: date.today().replace(day=1))
    date_to = factory.LazyFunction(lambda: date.today().replace(day=28))
    alert_threshold = None
    alert_sent_at = None
