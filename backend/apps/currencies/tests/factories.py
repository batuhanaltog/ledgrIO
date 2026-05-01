from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

import factory

from apps.currencies.models import Currency, FxRate


class CurrencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Currency
        django_get_or_create = ("code",)

    code = "USD"
    name = "US Dollar"
    symbol = "$"
    decimal_places = 2


class FxRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FxRate
        django_get_or_create = ("base_code", "quote_code", "rate_date")

    base_code = "USD"
    quote_code = "TRY"
    rate = Decimal("32.500000")
    rate_date = factory.LazyFunction(date_type.today)
