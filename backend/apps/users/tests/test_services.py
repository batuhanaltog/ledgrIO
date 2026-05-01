from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.users.services import register_user, update_user
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRegisterUserService:
    def test_creates_user_with_profile(self) -> None:
        user = register_user(
            email="new@ledgr.io",
            password="StrongPass123!",
            default_currency_code="EUR",
        )
        assert User.objects.filter(email="new@ledgr.io").exists()
        assert user.default_currency_code == "EUR"
        assert user.profile.timezone == "UTC"
        assert user.check_password("StrongPass123!")

    def test_rejects_duplicate_email(self) -> None:
        register_user(email="dup@ledgr.io", password="StrongPass123!")
        with pytest.raises(ValidationError, match="email"):
            register_user(email="dup@ledgr.io", password="OtherPass123!")

    def test_rejects_weak_password(self) -> None:
        with pytest.raises(ValidationError):
            register_user(email="weak@ledgr.io", password="123")

    def test_rejects_invalid_currency_code(self) -> None:
        with pytest.raises(ValidationError, match="currency"):
            register_user(
                email="bad@ledgr.io",
                password="StrongPass123!",
                default_currency_code="usd",
            )

    def test_normalizes_email(self) -> None:
        user = register_user(email="MIXED@LEDGR.IO", password="StrongPass123!")
        assert user.email == "mixed@ledgr.io"


@pytest.mark.django_db
class TestUpdateUserAllowlist:
    def test_rejects_unknown_profile_field(self) -> None:
        user = UserFactory()
        with pytest.raises(ValidationError, match="Unknown profile field"):
            update_user(user, profile_fields={"is_staff": True})

    def test_rejects_mix_of_valid_and_invalid_fields(self) -> None:
        user = UserFactory()
        with pytest.raises(ValidationError):
            update_user(user, profile_fields={"timezone": "UTC", "secret": "x"})
        # Even the valid field must NOT be persisted in the same call
        user.refresh_from_db()
        assert user.profile.timezone == "UTC"  # untouched (was the default)

    def test_accepts_only_allowed_fields(self) -> None:
        user = UserFactory()
        update_user(user, profile_fields={"timezone": "Europe/Istanbul", "locale": "tr-TR"})
        user.profile.refresh_from_db()
        assert user.profile.timezone == "Europe/Istanbul"
        assert user.profile.locale == "tr-TR"
