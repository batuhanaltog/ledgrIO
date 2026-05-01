"""User-related business logic — owns all writes per CLAUDE.md service pattern."""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import CURRENCY_CODE_VALIDATOR, User, UserProfile


def register_user(
    *,
    email: str,
    password: str,
    default_currency_code: str = "USD",
) -> User:
    """Create a User (and its profile via signal). Raises ValidationError on bad input.

    Validates the currency code, the password against Django's configured validators,
    and the email uniqueness constraint, all before any DB write.
    """
    try:
        CURRENCY_CODE_VALIDATOR(default_currency_code)
    except ValidationError as exc:
        raise ValidationError({"default_currency_code": exc.messages}) from exc

    validate_password(password)

    try:
        with transaction.atomic():
            return User.objects.create_user(
                email=email,
                password=password,
                default_currency_code=default_currency_code,
            )
    except IntegrityError as exc:
        raise ValidationError({"email": ["A user with this email already exists."]}) from exc


def update_user(
    user: User,
    *,
    default_currency_code: str | None = None,
    profile_fields: dict[str, object] | None = None,
) -> User:
    """Update mutable user + profile fields atomically."""
    with transaction.atomic():
        if default_currency_code is not None:
            CURRENCY_CODE_VALIDATOR(default_currency_code)
            user.default_currency_code = default_currency_code
            user.save(update_fields=["default_currency_code", "updated_at"])

        if profile_fields:
            profile: UserProfile = user.profile
            for field, value in profile_fields.items():
                setattr(profile, field, value)
            profile.full_clean()
            profile.save()

    user.refresh_from_db()
    return user
