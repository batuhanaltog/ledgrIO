from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from rest_framework import serializers

from .models import ACCOUNT_TYPE_CHOICES, Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields: ClassVar = [
            "id",
            "name",
            "account_type",
            "currency_code",
            "opening_balance",
            "is_active",
            "notes",
            "created_at",
        ]
        read_only_fields: ClassVar = ["id", "created_at"]


class AccountListSerializer(AccountSerializer):
    current_balance = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True
    )
    transaction_count = serializers.IntegerField(read_only=True)

    class Meta(AccountSerializer.Meta):
        fields: ClassVar = AccountSerializer.Meta.fields + [
            "current_balance",
            "transaction_count",
        ]
        read_only_fields: ClassVar = AccountSerializer.Meta.read_only_fields + [
            "current_balance",
            "transaction_count",
        ]


class AccountCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    account_type = serializers.ChoiceField(choices=[c[0] for c in ACCOUNT_TYPE_CHOICES])
    currency_code = serializers.CharField(max_length=10)
    opening_balance = serializers.DecimalField(
        max_digits=20, decimal_places=8, required=False, default=Decimal("0")
    )
    notes = serializers.CharField(allow_blank=True, required=False, default="")
    is_active = serializers.BooleanField(required=False, default=True)


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    account_type = serializers.ChoiceField(
        choices=[c[0] for c in ACCOUNT_TYPE_CHOICES], required=False
    )
    currency_code = serializers.CharField(max_length=10, required=False)
    opening_balance = serializers.DecimalField(
        max_digits=20, decimal_places=8, required=False
    )
    notes = serializers.CharField(allow_blank=True, required=False)
    is_active = serializers.BooleanField(required=False)


class ByAccountTypeSerializer(serializers.Serializer):
    account_type = serializers.CharField()
    total = serializers.DecimalField(max_digits=20, decimal_places=8)


class TotalAssetsSummarySerializer(serializers.Serializer):
    base_currency = serializers.CharField()
    total_assets = serializers.DecimalField(max_digits=20, decimal_places=8)
    by_account_type = ByAccountTypeSerializer(many=True)
    stale_fx_warning = serializers.BooleanField()
