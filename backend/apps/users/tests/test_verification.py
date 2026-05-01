"""Email verification — service + endpoint tests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import EmailVerificationToken
from apps.users.tests.factories import UserFactory
from apps.users.verification import (
    TokenInvalidError,
    issue_verification_token,
    send_verification_email,
    verify_email,
)


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache() -> None:
    cache.clear()


@pytest.mark.django_db
class TestIssueAndSend:
    def test_send_creates_token_and_outbox_entry(self, mailoutbox: list) -> None:
        user = UserFactory(email="verify@ledgr.io")
        token = send_verification_email(user)
        assert EmailVerificationToken.objects.filter(pk=token.pk).exists()
        assert len(mailoutbox) == 1
        msg = mailoutbox[0]
        assert msg.to == ["verify@ledgr.io"]
        assert token.token in msg.body

    def test_issue_invalidates_older_unused_tokens(self) -> None:
        user = UserFactory()
        first = issue_verification_token(user)
        second = issue_verification_token(user)
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.is_used  # superseded
        assert not second.is_used

    def test_register_endpoint_sends_verification_mail(
        self, mailoutbox: list
    ) -> None:
        api = APIClient()
        response = api.post(
            "/api/v1/auth/register/",
            {"email": "newreg@ledgr.io", "password": "StrongPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_email_verified"] is False
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["newreg@ledgr.io"]


@pytest.mark.django_db
class TestVerifyEmailService:
    def test_valid_token_flips_verified(self) -> None:
        user = UserFactory()
        token = issue_verification_token(user)
        verified = verify_email(token.token)
        assert verified.is_email_verified
        token.refresh_from_db()
        assert token.is_used

    def test_unknown_token_raises(self) -> None:
        with pytest.raises(TokenInvalidError, match="not recognised"):
            verify_email("not-a-real-token")

    def test_expired_token_raises(self) -> None:
        user = UserFactory()
        token = issue_verification_token(user)
        # Force expiry
        EmailVerificationToken.objects.filter(pk=token.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )
        with pytest.raises(TokenInvalidError, match="expired"):
            verify_email(token.token)

    def test_used_token_raises_on_second_use(self) -> None:
        user = UserFactory()
        token = issue_verification_token(user)
        verify_email(token.token)  # consume
        with pytest.raises(TokenInvalidError, match="already used"):
            verify_email(token.token)


@pytest.mark.django_db
class TestVerifyEmailEndpoint:
    URL = "/api/v1/auth/verify-email/"

    def test_endpoint_consumes_token(self) -> None:
        api = APIClient()
        user = UserFactory()
        token = issue_verification_token(user)
        response = api.post(self.URL, {"token": token.token}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_email_verified"] is True

    def test_endpoint_rejects_missing_token(self) -> None:
        api = APIClient()
        response = api.post(self.URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_endpoint_rejects_bad_token(self) -> None:
        api = APIClient()
        response = api.post(self.URL, {"token": "junk"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
