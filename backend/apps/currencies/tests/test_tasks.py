from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.currencies.models import FxRate
from celery_app.tasks.fx_tasks import fetch_daily_fx_rates


class _FakeProvider:
    def __init__(self, rates: dict[str, Decimal], rate_date: date) -> None:
        self._rates = rates
        self._date = rate_date

    def fetch_latest(self, *, base: str, symbols: list[str]):
        from apps.currencies.providers import LatestRates

        return LatestRates(base_code=base, rate_date=self._date, rates=self._rates)


@pytest.mark.django_db
def test_fetch_daily_fx_rates_writes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider(
        rates={"TRY": Decimal("32.5"), "EUR": Decimal("0.92"), "GBP": Decimal("0.78")},
        rate_date=date(2026, 5, 1),
    )
    monkeypatch.setattr(
        "celery_app.tasks.fx_tasks._build_provider", lambda: fake
    )

    written = fetch_daily_fx_rates(base="USD")
    assert written == 3
    assert FxRate.objects.filter(base_code="USD", rate_date=date(2026, 5, 1)).count() == 3
    assert (
        FxRate.objects.get(base_code="USD", quote_code="TRY", rate_date=date(2026, 5, 1)).rate
        == Decimal("32.5")
    )


@pytest.mark.django_db
def test_fetch_daily_fx_rates_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider(
        rates={"TRY": Decimal("32.5")},
        rate_date=date.today(),
    )
    monkeypatch.setattr(
        "celery_app.tasks.fx_tasks._build_provider", lambda: fake
    )

    fetch_daily_fx_rates(base="USD")
    fetch_daily_fx_rates(base="USD")  # second run must not crash on uniqueness
    assert FxRate.objects.filter(base_code="USD", rate_date=date.today()).count() == 1


@pytest.mark.django_db
def test_fetch_daily_fx_rates_skips_stale_provider_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider returning a 30-day-old snapshot must not be persisted."""
    stale = _FakeProvider(
        rates={"TRY": Decimal("32.5")},
        rate_date=date.today() - __import__("datetime").timedelta(days=30),
    )
    monkeypatch.setattr("celery_app.tasks.fx_tasks._build_provider", lambda: stale)
    written = fetch_daily_fx_rates(base="USD")
    assert written == 0
    assert FxRate.objects.filter(base_code="USD").count() == 0


@pytest.mark.django_db
def test_fetch_daily_fx_rates_skips_future_dated_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider returning a future date is suspicious — skip it."""
    future = _FakeProvider(
        rates={"TRY": Decimal("32.5")},
        rate_date=date.today() + __import__("datetime").timedelta(days=10),
    )
    monkeypatch.setattr("celery_app.tasks.fx_tasks._build_provider", lambda: future)
    written = fetch_daily_fx_rates(base="USD")
    assert written == 0
