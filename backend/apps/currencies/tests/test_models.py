from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.currencies.models import Currency, FxRate
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory


@pytest.mark.django_db
class TestCurrency:
    def test_seed_migration_loads_iso_and_crypto_codes(self) -> None:
        codes = set(Currency.objects.values_list("code", flat=True))
        assert {"TRY", "USD", "EUR", "GBP", "BTC", "ETH"}.issubset(codes)

    def test_code_is_primary_key(self) -> None:
        c = CurrencyFactory(code="JPY", name="Japanese Yen", symbol="¥", decimal_places=0)
        assert c.pk == "JPY"

    def test_str_returns_code(self) -> None:
        assert str(CurrencyFactory(code="USD")) == "USD"

    def test_btc_uses_eight_decimals(self) -> None:
        btc = Currency.objects.get(code="BTC")
        assert btc.decimal_places == 8


@pytest.mark.django_db
class TestFxRate:
    def test_unique_per_pair_and_date(self) -> None:
        FxRateFactory(base_code="USD", quote_code="TRY", rate_date=date(2026, 5, 1))
        with pytest.raises(IntegrityError):
            FxRate.objects.create(
                base_code="USD",
                quote_code="TRY",
                rate=Decimal("33.0"),
                rate_date=date(2026, 5, 1),
            )

    def test_base_and_quote_must_differ(self) -> None:
        from django.core.exceptions import ValidationError

        rate = FxRate(
            base_code="USD",
            quote_code="USD",
            rate=Decimal("1.0"),
            rate_date=date(2026, 5, 1),
        )
        with pytest.raises(ValidationError):
            rate.full_clean()

    def test_default_ordering_newest_first(self) -> None:
        FxRateFactory(rate_date=date(2026, 1, 1))
        FxRateFactory(rate_date=date(2026, 5, 1))
        FxRateFactory(rate_date=date(2026, 3, 1))
        dates = list(FxRate.objects.values_list("rate_date", flat=True))
        assert dates == sorted(dates, reverse=True)
