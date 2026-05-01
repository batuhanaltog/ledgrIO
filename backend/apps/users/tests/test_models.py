from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.users.tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserManager:
    def test_create_user_with_email_and_password(self) -> None:
        user = User.objects.create_user(email="alice@ledgr.io", password="StrongPass123!")
        assert user.email == "alice@ledgr.io"
        assert user.check_password("StrongPass123!")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_normalizes_email_to_lowercase(self) -> None:
        # Both local-part and domain are lowercased to keep auth case-insensitive.
        user = User.objects.create_user(email="Bob@LEDGR.IO", password="StrongPass123!")
        assert user.email == "bob@ledgr.io"

    def test_create_user_requires_email(self) -> None:
        with pytest.raises(ValueError, match="email"):
            User.objects.create_user(email="", password="StrongPass123!")

    def test_create_superuser(self) -> None:
        admin = User.objects.create_superuser(email="root@ledgr.io", password="StrongPass123!")
        assert admin.is_superuser is True
        assert admin.is_staff is True


@pytest.mark.django_db
class TestUserModel:
    def test_email_is_unique(self) -> None:
        UserFactory(email="dup@ledgr.io")
        with pytest.raises(IntegrityError):
            UserFactory(email="dup@ledgr.io")

    def test_username_field_is_email(self) -> None:
        assert User.USERNAME_FIELD == "email"
        assert "username" not in [f.name for f in User._meta.get_fields()]

    def test_required_fields_excludes_email(self) -> None:
        # USERNAME_FIELD is email; REQUIRED_FIELDS should not contain it
        assert "email" not in User.REQUIRED_FIELDS

    def test_default_currency_defaults_to_usd(self) -> None:
        user = UserFactory()
        assert user.default_currency_code == "USD"

    def test_default_currency_validation_rejects_lowercase(self) -> None:
        from django.core.exceptions import ValidationError

        user = UserFactory(default_currency_code="usd")
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_str_returns_email(self) -> None:
        user = UserFactory(email="hello@ledgr.io")
        assert str(user) == "hello@ledgr.io"


@pytest.mark.django_db
class TestUserProfileAutoCreated:
    def test_profile_created_on_user_creation(self) -> None:
        user = UserFactory()
        assert user.profile is not None
        assert user.profile.timezone == "UTC"
        assert user.profile.locale == "en-US"
        assert user.profile.monthly_income is None
