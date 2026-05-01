"""Periodic FX rate refresh."""
from __future__ import annotations

import logging
from datetime import date, timedelta

import requests
from celery import shared_task

from apps.currencies.providers import FrankfurterProvider, FxProvider
from apps.currencies.services import upsert_rate

logger = logging.getLogger(__name__)

# Reject snapshots older than this — protects us from a provider serving stale
# data due to outages, weekends, or upstream cache layers.
MAX_RATE_AGE_DAYS = 7


def _build_provider() -> FxProvider:
    """Indirection so tests can patch the provider easily."""
    return FrankfurterProvider()


@shared_task(
    name="currencies.fetch_daily_fx_rates",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def fetch_daily_fx_rates(base: str = "USD") -> int:
    """Fetch the latest fiat FX snapshot and write it to the DB. Returns rows written.

    Skips writes when the provider returns a snapshot older than MAX_RATE_AGE_DAYS;
    this guards against silently serving stale rates after a provider incident.
    """
    provider = _build_provider()
    symbols = ["TRY", "EUR", "GBP"]
    latest = provider.fetch_latest(base=base, symbols=symbols)

    today = date.today()
    age = (today - latest.rate_date).days
    if age > MAX_RATE_AGE_DAYS:
        logger.warning(
            "Skipping FX upsert: provider returned stale snapshot from %s (%d days old)",
            latest.rate_date,
            age,
        )
        return 0
    if latest.rate_date > today + timedelta(days=1):
        logger.warning(
            "Skipping FX upsert: provider returned future-dated snapshot %s",
            latest.rate_date,
        )
        return 0

    written = 0
    for quote, rate in latest.rates.items():
        upsert_rate(base=latest.base_code, quote=quote, rate=rate, rate_date=latest.rate_date)
        written += 1
    return written
