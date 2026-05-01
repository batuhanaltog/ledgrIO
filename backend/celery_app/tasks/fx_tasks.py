"""Periodic FX rate refresh."""
from __future__ import annotations

from celery import shared_task

from apps.currencies.providers import FrankfurterProvider, FxProvider
from apps.currencies.services import upsert_rate


def _build_provider() -> FxProvider:
    """Indirection so tests can patch the provider easily."""
    return FrankfurterProvider()


@shared_task(name="currencies.fetch_daily_fx_rates")
def fetch_daily_fx_rates(base: str = "USD") -> int:
    """Fetch the latest fiat FX snapshot and write it to the DB. Returns rows written."""
    provider = _build_provider()
    symbols = ["TRY", "EUR", "GBP"]
    latest = provider.fetch_latest(base=base, symbols=symbols)
    written = 0
    for quote, rate in latest.rates.items():
        upsert_rate(base=latest.base_code, quote=quote, rate=rate, rate_date=latest.rate_date)
        written += 1
    return written
