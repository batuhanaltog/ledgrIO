from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

import factory

from apps.transactions.models import EXPENSE, Transaction
from apps.users.tests.factories import UserFactory


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SubFactory(UserFactory)
    type = EXPENSE
    amount = Decimal("100.00000000")
    currency_code = "USD"
    amount_base = Decimal("100.00000000")
    base_currency = "USD"
    fx_rate_snapshot = Decimal("1.00000000")
    category = None
    date = factory.LazyFunction(date_type.today)
    description = ""
    reference = ""
