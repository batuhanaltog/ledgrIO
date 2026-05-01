"""External FX provider adapters.

Frankfurter.dev is used as the default provider — free, no API key, fiat only.
Crypto rates are intentionally out of scope here; they will be added via a
CoinGecko adapter in a later phase alongside the portfolio module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Protocol

import requests

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"


@dataclass(frozen=True)
class LatestRates:
    base_code: str
    rate_date: date_type
    rates: dict[str, Decimal]


class FxProvider(Protocol):
    def fetch_latest(self, *, base: str, symbols: list[str]) -> LatestRates: ...


class FrankfurterProvider:
    """Fiat FX rates from frankfurter.dev (no auth required)."""

    def fetch_latest(self, *, base: str, symbols: list[str]) -> LatestRates:
        response = requests.get(
            f"{FRANKFURTER_BASE_URL}/latest",
            params={"base": base, "symbols": ",".join(symbols)},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return LatestRates(
            base_code=payload["base"],
            rate_date=datetime.strptime(payload["date"], "%Y-%m-%d").date(),
            rates={code: Decimal(str(rate)) for code, rate in payload["rates"].items()},
        )
