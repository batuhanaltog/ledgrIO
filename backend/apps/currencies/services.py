"""Currency conversion + write helpers — owns all FX writes."""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Final

from django.core.cache import cache
from django.db import transaction

from .models import Currency, FxRate

CACHE_TTL_SECONDS: Final[int] = 60 * 60  # 1 hour
QUANTIZE = Decimal("0.00000001")


class RateNotFoundError(LookupError):
    """No FX rate available for the requested pair on or before the given date."""


class UnknownCurrencyError(ValueError):
    """An FX write was attempted for a currency not present in the Currency catalog."""


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


def get_exchange_rate(from_code: str, to_code: str, *, at: date_type) -> Decimal:
    """Return the raw exchange rate for a currency pair at the given date.

    Uses the same direct/inverse/fallback logic as _lookup_rate. Used when
    callers need the rate itself (e.g. to store as fx_rate_snapshot).
    """
    if from_code == to_code:
        return Decimal("1")
    rate = _lookup_rate(from_code, to_code, at)
    if rate is None:
        raise RateNotFoundError(f"No FX rate for {from_code}->{to_code} on or before {at}")
    return rate


def upsert_rate(*, base: str, quote: str, rate: Decimal, rate_date: date_type) -> FxRate:
    """Idempotent insert/update of an FX snapshot.

    FxRate stores currency codes as strings (not FK to Currency) to avoid JOIN
    cost on every conversion. This guard is the app-level substitute for an FK
    constraint: it ensures both codes exist in the Currency catalog before write,
    so we can never produce orphan rows even if a future caller bypasses the
    Frankfurter task. Postgres CHECK constraints can't do cross-table lookups
    cleanly, so this lives in the service rather than the schema.
    """
    known = set(Currency.objects.filter(code__in=(base, quote)).values_list("code", flat=True))
    missing = {base, quote} - known
    if missing:
        raise UnknownCurrencyError(
            f"Cannot write FX rate; unknown currency code(s) in catalog: {sorted(missing)}"
        )

    with transaction.atomic():
        obj, _ = FxRate.objects.update_or_create(
            base_code=base,
            quote_code=quote,
            rate_date=rate_date,
            defaults={"rate": rate},
        )
        cache.delete(_cache_key(base, quote, rate_date))
    return obj
