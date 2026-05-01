"""Email verification service layer.

Phase 3.5 scaffold. Mail goes to the console backend in dev; production just
needs EMAIL_BACKEND switched to a real provider (e.g. Anymail+Mailgun). Token
model lives in models.py so django-stubs can find it; this module owns
behavior.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailVerificationToken, User

TOKEN_TTL = timedelta(hours=24)


class TokenInvalidError(ValueError):
    """The supplied verification token is unknown, expired, or already consumed."""


def issue_verification_token(user: User) -> EmailVerificationToken:
    """Mint a fresh token. Older unused tokens for the same user are invalidated."""
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    return EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + TOKEN_TTL,
    )


def send_verification_email(user: User) -> EmailVerificationToken:
    """Issue a token and dispatch the verification email (console backend in dev)."""
    token = issue_verification_token(user)
    send_mail(
        subject="Confirm your Ledgr.io email address",
        message=(
            f"Hi,\n\n"
            f"Please confirm your email by submitting this token:\n\n  {token.token}\n\n"
            f"It expires in 24 hours.\n"
        ),
        from_email="no-reply@ledgr.io",
        recipient_list=[user.email],
        fail_silently=False,
    )
    return token


def verify_email(token_str: str) -> User:
    """Consume a token. Raises TokenInvalidError on unknown/expired/used tokens."""
    try:
        token = EmailVerificationToken.objects.select_related("user").get(token=token_str)
    except EmailVerificationToken.DoesNotExist as exc:
        raise TokenInvalidError("Token not recognised.") from exc

    if token.is_expired:
        raise TokenInvalidError("Token has expired.")
    if token.is_used:
        raise TokenInvalidError("Token already used.")

    token.used_at = timezone.now()
    token.save(update_fields=["used_at", "updated_at"])

    if not token.user.is_email_verified:
        token.user.is_email_verified = True
        token.user.save(update_fields=["is_email_verified", "updated_at"])

    return token.user
