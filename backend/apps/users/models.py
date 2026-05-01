"""User, UserProfile, and EmailVerificationToken models."""
from __future__ import annotations

import secrets
from decimal import Decimal
from typing import ClassVar, Final

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from common.models import TimestampedModel

from .managers import UserManager

VERIFICATION_TOKEN_BYTES: Final[int] = 32  # ~256 bits of entropy

CURRENCY_CODE_VALIDATOR = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Currency code must be 3 uppercase letters (ISO 4217).",
)


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    """Email-authenticated user."""

    email = models.EmailField(unique=True, db_index=True)
    default_currency_code = models.CharField(
        max_length=3,
        default="USD",
        validators=[CURRENCY_CODE_VALIDATOR],
        help_text="ISO 4217 code; will be promoted to a Currency FK in Phase 2.",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Set to True once the user clicks their verification link.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()

    class Meta:
        db_table = "users_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email


class UserProfile(TimestampedModel):
    """Per-user preferences and lightweight personal data."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )
    timezone = models.CharField(max_length=63, default="UTC")
    locale = models.CharField(max_length=10, default="en-US")
    monthly_income = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Stored in user's default currency. Used as a budgeting hint.",
    )

    class Meta:
        db_table = "users_userprofile"

    def __str__(self) -> str:
        return f"profile<{self.user.email}>"

    @property
    def has_income_set(self) -> bool:
        return self.monthly_income is not None and self.monthly_income > Decimal("0")


def _new_verification_token() -> str:
    return secrets.token_urlsafe(VERIFICATION_TOKEN_BYTES)


class EmailVerificationToken(TimestampedModel):
    """One-shot, time-bounded token a user presents to verify their email."""

    token = models.CharField(
        max_length=128, unique=True, default=_new_verification_token, db_index=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_tokens")
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users_emailverificationtoken"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"verify<{self.user.email}>"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
