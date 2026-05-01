from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.currencies.providers import FrankfurterProvider


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_frankfurter_parses_latest_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "amount": 1.0,
        "base": "USD",
        "date": "2026-05-01",
        "rates": {"TRY": 32.5, "EUR": 0.92},
    }
    captured: dict = {}

    def fake_get(url: str, params: dict, timeout: int) -> FakeResponse:
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(payload)

    monkeypatch.setattr("apps.currencies.providers.requests.get", fake_get)

    provider = FrankfurterProvider()
    rates = provider.fetch_latest(base="USD", symbols=["TRY", "EUR"])

    assert rates.base_code == "USD"
    assert rates.rate_date == date(2026, 5, 1)
    assert rates.rates["TRY"] == Decimal("32.5")
    assert rates.rates["EUR"] == Decimal("0.92")
    assert captured["params"]["base"] == "USD"
    assert captured["params"]["symbols"] == "TRY,EUR"


def test_frankfurter_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, params: dict, timeout: int) -> FakeResponse:
        return FakeResponse({}, status_code=503)

    monkeypatch.setattr("apps.currencies.providers.requests.get", fake_get)

    with pytest.raises(RuntimeError, match="503"):
        FrankfurterProvider().fetch_latest(base="USD", symbols=["TRY"])
