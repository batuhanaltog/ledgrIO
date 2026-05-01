from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.currencies.tests.factories import FxRateFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def authed() -> APIClient:
    client = APIClient()
    user = UserFactory(email="cur@ledgr.io")
    login = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "VerySecret123!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client


@pytest.mark.django_db
class TestCurrencyListEndpoint:
    URL = "/api/v1/currencies/"

    def test_requires_authentication(self) -> None:
        client = APIClient()
        response = client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_seeded_currencies(self, authed: APIClient) -> None:
        response = authed.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        codes = {row["code"] for row in response.data["results"]}
        assert {"TRY", "USD", "EUR", "GBP", "BTC", "ETH"}.issubset(codes)


@pytest.mark.django_db
class TestFxRateEndpoint:
    URL = "/api/v1/fx/"

    def test_returns_latest_rate(self, authed: APIClient) -> None:
        FxRateFactory(
            base_code="USD",
            quote_code="TRY",
            rate=Decimal("32.5"),
            rate_date=date(2026, 5, 1),
        )
        response = authed.get(f"{self.URL}?base=USD&quote=TRY")
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(str(response.data["rate"])) == Decimal("32.5")
        assert response.data["base"] == "USD"
        assert response.data["quote"] == "TRY"

    def test_returns_404_when_no_rate(self, authed: APIClient) -> None:
        response = authed.get(f"{self.URL}?base=USD&quote=JPY")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validates_query_params(self, authed: APIClient) -> None:
        response = authed.get(self.URL)  # missing base, quote
        assert response.status_code == status.HTTP_400_BAD_REQUEST
