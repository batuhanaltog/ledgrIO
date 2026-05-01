"""DRF serializers for the users app."""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserProfile
from .services import register_user, update_user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("timezone", "locale", "monthly_income")


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "default_currency_code",
            "is_email_verified",
            "profile",
            "date_joined",
        )
        read_only_fields = ("id", "email", "is_email_verified", "date_joined")

    date_joined = serializers.DateTimeField(source="created_at", read_only=True)

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        profile_data = validated_data.pop("profile", None)
        try:
            return update_user(
                instance,
                default_currency_code=validated_data.get("default_currency_code"),
                profile_fields=profile_data,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # No min_length here — Django's AUTH_PASSWORD_VALIDATORS is the single
    # source of truth (see settings.base.AUTH_PASSWORD_VALIDATORS). The service
    # calls validate_password() which enforces all configured validators.
    password = serializers.CharField(write_only=True, max_length=128)
    default_currency_code = serializers.CharField(default="USD", max_length=3)

    def create(self, validated_data: dict[str, Any]) -> User:
        try:
            return register_user(**validated_data)
        except DjangoValidationError as exc:
            # validate_password() raises a list-shaped ValidationError, while
            # service-level errors raise dict-shaped. Normalize to "password" key
            # when the message has no field association.
            detail = exc.message_dict if hasattr(exc, "error_dict") else {"password": exc.messages}
            raise serializers.ValidationError(detail) from exc

    def to_representation(self, instance: User) -> dict[str, Any]:
        return UserSerializer(instance).data


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login by email instead of username."""

    username_field = User.USERNAME_FIELD
