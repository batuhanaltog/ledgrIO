"""User-related business logic — owns all writes per CLAUDE.md service pattern."""
from __future__ import annotations

from typing import Final

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import CURRENCY_CODE_VALIDATOR, User, UserProfile

# Defense-in-depth: serializer already restricts via Meta.fields, but the
# service must reject unknown keys too in case it's called from other code paths.
ALLOWED_PROFILE_FIELDS: Final[frozenset[str]] = frozenset(
    {"timezone", "locale", "monthly_income"}
)


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
            user = User.objects.create_user(
                email=email,
                password=password,
                default_currency_code=default_currency_code,
            )
    except IntegrityError as exc:
        raise ValidationError({"email": ["A user with this email already exists."]}) from exc

    # Fire the verification email after the user-create transaction commits;
    # mail failure must not roll back the registration.
    from .verification import send_verification_email

    send_verification_email(user)
    return user


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
            unknown = set(profile_fields) - ALLOWED_PROFILE_FIELDS
            if unknown:
                raise ValidationError(
                    {"profile": [f"Unknown profile field(s): {sorted(unknown)}"]}
                )
            profile: UserProfile = user.profile
            for field, value in profile_fields.items():
                setattr(profile, field, value)
            profile.full_clean()
            profile.save()

    user.refresh_from_db()
    return user
