from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache

from apps.currencies.services import RateNotFoundError, convert
from apps.currencies.tests.factories import FxRateFactory


@pytest.fixture(autouse=True)
def _flush_cache() -> None:
    cache.clear()


@pytest.mark.django_db
class TestConvert:
    def test_same_currency_is_identity(self) -> None:
        result = convert(Decimal("123.456"), "USD", "USD", at=date(2026, 5, 1))
        assert result == Decimal("123.456")

    def test_uses_direct_rate(self) -> None:
        FxRateFactory(
            base_code="USD",
            quote_code="TRY",
            rate=Decimal("32.5"),
            rate_date=date(2026, 5, 1),
        )
        result = convert(Decimal("10"), "USD", "TRY", at=date(2026, 5, 1))
        assert result == Decimal("325.00000000")

    def test_uses_inverse_rate_when_direct_missing(self) -> None:
        FxRateFactory(
            base_code="USD",
            quote_code="TRY",
            rate=Decimal("32.5"),
            rate_date=date(2026, 5, 1),
        )
        # No TRY->USD row; inverse should be 1/32.5
        result = convert(Decimal("325"), "TRY", "USD", at=date(2026, 5, 1))
        assert result.quantize(Decimal("0.01")) == Decimal("10.00")

    def test_falls_back_to_latest_rate_before_requested_date(self) -> None:
        FxRateFactory(
            base_code="USD",
            quote_code="TRY",
            rate=Decimal("30.0"),
            rate_date=date(2026, 4, 1),
        )
        # Request on May 1, only have April 1 — should use April 1 rate
        result = convert(Decimal("1"), "USD", "TRY", at=date(2026, 5, 1))
        assert result == Decimal("30.00000000")

    def test_raises_when_no_rate_available(self) -> None:
        with pytest.raises(RateNotFoundError):
            convert(Decimal("1"), "USD", "JPY", at=date(2026, 5, 1))

    def test_caches_lookup(self, django_assert_num_queries) -> None:
        FxRateFactory(
            base_code="USD",
            quote_code="TRY",
            rate=Decimal("32.5"),
            rate_date=date(2026, 5, 1),
        )
        convert(Decimal("1"), "USD", "TRY", at=date(2026, 5, 1))
        # Second call must not hit the DB
        with django_assert_num_queries(0):
            convert(Decimal("1"), "USD", "TRY", at=date(2026, 5, 1))
