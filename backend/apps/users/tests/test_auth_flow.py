"""End-to-end auth flow — exercises register → login → me → patch → refresh → logout.

Per-endpoint tests catch unit-level regressions; this catches contract
mismatches between endpoints (e.g. login response shape diverging from what
refresh expects).
"""
from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User


@pytest.fixture(autouse=True)
def _reset_ratelimit_cache() -> None:
    cache.clear()


@pytest.mark.django_db
def test_full_auth_lifecycle() -> None:
    """A new user can register, log in, read & patch their profile,
    rotate their refresh token, and log out — and the rotated/blacklisted
    tokens must stop working afterwards.
    """
    api = APIClient()

    # 1. Register
    register = api.post(
        "/api/v1/auth/register/",
        {
            "email": "lifecycle@ledgr.io",
            "password": "SuperSecret123!",
            "default_currency_code": "EUR",
        },
        format="json",
    )
    assert register.status_code == status.HTTP_201_CREATED
    assert "password" not in register.data
    user_id = register.data["id"]

    # 2. Login
    login = api.post(
        "/api/v1/auth/login/",
        {"email": "lifecycle@ledgr.io", "password": "SuperSecret123!"},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK
    access = login.data["access"]
    refresh = login.data["refresh"]

    # JWT claims sanity check (audit 2.4)
    decoded = AccessToken(access)
    assert decoded["user_id"] == user_id
    assert "exp" in decoded
    assert "iat" in decoded

    # 3. /me with the access token
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = api.get("/api/v1/users/me/")
    assert me.status_code == status.HTTP_200_OK
    assert me.data["email"] == "lifecycle@ledgr.io"
    assert me.data["default_currency_code"] == "EUR"

    # 4. PATCH profile
    patched = api.patch(
        "/api/v1/users/me/",
        {"profile": {"timezone": "Europe/Istanbul", "locale": "tr-TR"}},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["profile"]["timezone"] == "Europe/Istanbul"

    # 5. Refresh — gets a new access token AND rotates the refresh
    refreshed = api.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
    assert refreshed.status_code == status.HTTP_200_OK
    new_access = refreshed.data["access"]
    new_refresh = refreshed.data["refresh"]
    assert new_access != access
    assert new_refresh != refresh

    # The OLD refresh must be blacklisted by rotation.
    old_refresh_retry = api.post(
        "/api/v1/auth/refresh/", {"refresh": refresh}, format="json"
    )
    assert old_refresh_retry.status_code == status.HTTP_401_UNAUTHORIZED

    # 6. Logout — blacklist the new refresh
    logout = api.post("/api/v1/auth/logout/", {"refresh": new_refresh}, format="json")
    assert logout.status_code == status.HTTP_205_RESET_CONTENT

    # The new refresh must also fail now.
    after_logout = api.post(
        "/api/v1/auth/refresh/", {"refresh": new_refresh}, format="json"
    )
    assert after_logout.status_code == status.HTTP_401_UNAUTHORIZED

    # User row was actually persisted with the patched fields
    user = User.objects.get(id=user_id)
    assert user.email == "lifecycle@ledgr.io"
    assert user.profile.timezone == "Europe/Istanbul"


@pytest.mark.django_db
def test_login_with_uppercase_email_works(api: APIClient = None) -> None:  # type: ignore[assignment]
    """Audit 2.5: register lowercases the domain — login must too."""
    api = APIClient()
    api.post(
        "/api/v1/auth/register/",
        {"email": "Casey@LEDGR.IO", "password": "SuperSecret123!"},
        format="json",
    )
    login = api.post(
        "/api/v1/auth/login/",
        {"email": "casey@ledgr.io", "password": "SuperSecret123!"},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK
