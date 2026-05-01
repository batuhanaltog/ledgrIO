"""HTTP layer for the users app — thin, delegates to services."""
from __future__ import annotations

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .verification import (
    TokenInvalidError,
    confirm_password_reset,
    request_password_reset,
    verify_email,
)


@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()


@method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True), name="post")
class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer  # type: ignore[assignment]
    permission_classes = (AllowAny,)  # type: ignore[assignment]
    authentication_classes = ()


class RefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)  # type: ignore[assignment]
    authentication_classes = ()


class LogoutView(APIView):
    """Blacklists the supplied refresh token."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}},
        responses={205: None, 400: None},
    )
    def post(self, request: Request) -> Response:
        token_str = request.data.get("refresh")
        if not token_str:
            return Response(
                {"detail": "refresh token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token_str).blacklist()
        except TokenError:
            return Response(
                {"detail": "invalid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> User:
        # IsAuthenticated permission guarantees this is a real User, not Anonymous.
        return self.request.user  # type: ignore[return-value]


class PasswordResetRequestView(APIView):
    """Send a password reset email. Always 200 to prevent enumeration."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"email": {"type": "string"}}}},
        responses={200: None},
    )
    def post(self, request: Request) -> Response:
        email = request.data.get("email", "")
        if not email:
            return Response({"detail": "email required"}, status=status.HTTP_400_BAD_REQUEST)
        request_password_reset(email=str(email))
        return Response({"detail": "If that email is registered, a reset link has been sent."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Consume a reset token and set a new password."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"token": {"type": "string"}, "new_password": {"type": "string"}}}},
        responses={200: None, 400: None},
    )
    def post(self, request: Request) -> Response:
        token_str = request.data.get("token")
        new_password = request.data.get("new_password")
        if not token_str or not new_password:
            return Response({"detail": "token and new_password required"}, status=status.HTTP_400_BAD_REQUEST)
        if len(str(new_password)) < 10:
            return Response({"detail": "Password must be at least 10 characters."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            confirm_password_reset(token_str=str(token_str), new_password=str(new_password))
        except TokenInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """Consume a verification token and flip is_email_verified."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"token": {"type": "string"}}}},
        responses={200: None, 400: None},
    )
    def post(self, request: Request) -> Response:
        token_str = request.data.get("token")
        if not token_str:
            return Response(
                {"detail": "token required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = verify_email(token_str)
        except TokenInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"email": user.email, "is_email_verified": user.is_email_verified},
            status=status.HTTP_200_OK,
        )
