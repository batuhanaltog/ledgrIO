from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.users.services import register_user


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
        assert user.email == "MIXED@ledgr.io"
