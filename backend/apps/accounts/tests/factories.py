from __future__ import annotations

from decimal import Decimal

import factory

from apps.accounts.models import Account
from apps.users.tests.factories import UserFactory


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Account {n}")
    account_type = "bank"
    currency_code = "USD"
    opening_balance = Decimal("0.00000000")
    is_active = True
    notes = ""
