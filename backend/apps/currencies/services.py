"""Currency conversion + write helpers — owns all FX writes."""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Final

from django.core.cache import cache
from django.db import transaction

from .models import FxRate

CACHE_TTL_SECONDS: Final[int] = 60 * 60  # 1 hour
QUANTIZE = Decimal("0.00000001")


class RateNotFoundError(LookupError):
    """No FX rate available for the requested pair on or before the given date."""


def _cache_key(base: str, quote: str, at: date_type) -> str:
    return f"fx:{base}:{quote}:{at.isoformat()}"


def _lookup_rate(base: str, quote: str, at: date_type) -> Decimal | None:
    """Return the most recent raw rate at or before `at`. Tries direct, then inverse.

    Returned value is unquantized so the caller can do `amount * rate` once and
    quantize the final product — avoids compounding rounding (audit finding 1.8).
    """
    direct = (
        FxRate.objects.filter(base_code=base, quote_code=quote, rate_date__lte=at)
        .order_by("-rate_date")
        .values_list("rate", flat=True)
        .first()
    )
    if direct is not None:
        return Decimal(direct)

    inverse = (
        FxRate.objects.filter(base_code=quote, quote_code=base, rate_date__lte=at)
        .order_by("-rate_date")
        .values_list("rate", flat=True)
        .first()
    )
    if inverse is not None:
        return Decimal("1") / Decimal(inverse)

    return None


def convert(amount: Decimal, from_code: str, to_code: str, *, at: date_type) -> Decimal:
    """Convert `amount` from `from_code` to `to_code` using the snapshot at `at`.

    Quantizes once, at the end. Multiplies amount by the raw rate to preserve
    precision through inverse-rate paths.
    """
    if from_code == to_code:
        return amount

    key = _cache_key(from_code, to_code, at)
    cached = cache.get(key)
    if cached is not None:
        return (amount * Decimal(cached)).quantize(QUANTIZE)

    rate = _lookup_rate(from_code, to_code, at)
    if rate is None:
        raise RateNotFoundError(f"No FX rate for {from_code}->{to_code} on or before {at}")

    # Cache the raw rate so subsequent calls keep precision.
    cache.set(key, str(rate), CACHE_TTL_SECONDS)
    return (amount * rate).quantize(QUANTIZE)


def upsert_rate(*, base: str, quote: str, rate: Decimal, rate_date: date_type) -> FxRate:
    """Idempotent insert/update of an FX snapshot."""
    with transaction.atomic():
        obj, _ = FxRate.objects.update_or_create(
            base_code=base,
            quote_code=quote,
            rate_date=rate_date,
            defaults={"rate": rate},
        )
        cache.delete(_cache_key(base, quote, rate_date))
    return obj
