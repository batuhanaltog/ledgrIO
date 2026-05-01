from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User
from apps.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache() -> None:
    """django-ratelimit stores counters in cache; isolate between tests."""
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def authed_api(api: APIClient) -> tuple[APIClient, User]:
    user = UserFactory(email="me@ledgr.io")
    response = api.post(
        "/api/v1/auth/login/",
        {"email": "me@ledgr.io", "password": "VerySecret123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api, user


@pytest.mark.django_db
class TestRegisterEndpoint:
    URL = "/api/v1/auth/register/"

    def test_register_creates_user(self, api: APIClient) -> None:
        response = api.post(
            self.URL,
            {
                "email": "alice@ledgr.io",
                "password": "StrongPass123!",
                "default_currency_code": "USD",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["email"] == "alice@ledgr.io"
        assert "password" not in response.data
        assert User.objects.filter(email="alice@ledgr.io").exists()

    def test_register_rejects_duplicate_email(self, api: APIClient) -> None:
        UserFactory(email="taken@ledgr.io")
        response = api.post(
            self.URL,
            {"email": "taken@ledgr.io", "password": "StrongPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_rejects_weak_password(self, api: APIClient) -> None:
        response = api.post(
            self.URL,
            {"email": "weak@ledgr.io", "password": "123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginEndpoint:
    URL = "/api/v1/auth/login/"

    def test_login_returns_token_pair(self, api: APIClient) -> None:
        UserFactory(email="login@ledgr.io")
        response = api.post(
            self.URL,
            {"email": "login@ledgr.io", "password": "VerySecret123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_rejects_wrong_password(self, api: APIClient) -> None:
        UserFactory(email="user@ledgr.io")
        response = api.post(
            self.URL,
            {"email": "user@ledgr.io", "password": "WRONG"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_rejects_unknown_user(self, api: APIClient) -> None:
        response = api.post(
            self.URL,
            {"email": "ghost@ledgr.io", "password": "VerySecret123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRefreshAndLogout:
    def test_refresh_returns_new_access(self, api: APIClient) -> None:
        UserFactory(email="r@ledgr.io")
        login = api.post(
            "/api/v1/auth/login/",
            {"email": "r@ledgr.io", "password": "VerySecret123!"},
            format="json",
        )
        refresh_token = login.data["refresh"]

        response = api.post(
            "/api/v1/auth/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_logout_blacklists_refresh_token(self, api: APIClient) -> None:
        UserFactory(email="lo@ledgr.io")
        login = api.post(
            "/api/v1/auth/login/",
            {"email": "lo@ledgr.io", "password": "VerySecret123!"},
            format="json",
        )
        refresh_token = login.data["refresh"]

        logout = api.post(
            "/api/v1/auth/logout/",
            {"refresh": refresh_token},
            format="json",
        )
        assert logout.status_code == status.HTTP_205_RESET_CONTENT

        # Using the blacklisted refresh again must fail
        retry = api.post(
            "/api/v1/auth/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert retry.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMeEndpoint:
    URL = "/api/v1/users/me/"

    def test_me_requires_authentication(self, api: APIClient) -> None:
        response = api.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_current_user(self, authed_api: tuple[APIClient, User]) -> None:
        api, user = authed_api
        response = api.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["profile"]["timezone"] == "UTC"

    def test_me_patch_updates_profile_fields(
        self, authed_api: tuple[APIClient, User]
    ) -> None:
        api, _ = authed_api
        response = api.patch(
            self.URL,
            {
                "default_currency_code": "TRY",
                "profile": {"timezone": "Europe/Istanbul", "locale": "tr-TR"},
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["default_currency_code"] == "TRY"
        assert response.data["profile"]["timezone"] == "Europe/Istanbul"
        assert response.data["profile"]["locale"] == "tr-TR"


@pytest.mark.django_db
class TestRateLimits:
    def test_login_blocks_after_burst(self, api: APIClient) -> None:
        UserFactory(email="rl@ledgr.io")
        # Rate is 10/minute on POST /auth/login/. 11th must 429.
        for _ in range(10):
            r = api.post(
                "/api/v1/auth/login/",
                {"email": "rl@ledgr.io", "password": "wrong"},
                format="json",
            )
            assert r.status_code == status.HTTP_401_UNAUTHORIZED
        blocked = api.post(
            "/api/v1/auth/login/",
            {"email": "rl@ledgr.io", "password": "wrong"},
            format="json",
        )
        assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_register_blocks_after_burst(self, api: APIClient) -> None:
        # Rate is 5/h on POST /auth/register/. 6th must 429.
        for i in range(5):
            r = api.post(
                "/api/v1/auth/register/",
                {"email": f"u{i}@ledgr.io", "password": "StrongPass123!"},
                format="json",
            )
            assert r.status_code == status.HTTP_201_CREATED
        blocked = api.post(
            "/api/v1/auth/register/",
            {"email": "u99@ledgr.io", "password": "StrongPass123!"},
            format="json",
        )
        assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
