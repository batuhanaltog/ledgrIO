from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from rest_framework import serializers

from apps.budgets.models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    spent = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True, default=Decimal("0")
    )
    remaining = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True, default=Decimal("0")
    )
    usage_pct = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True, default=Decimal("0")
    )

    class Meta:
        model = Budget
        fields: ClassVar = [
            "id",
            "name",
            "category",
            "amount",
            "date_from",
            "date_to",
            "alert_threshold",
            "alert_sent_at",
            "spent",
            "remaining",
            "usage_pct",
            "created_at",
            "updated_at",
        ]
        read_only_fields: ClassVar = [
            "id",
            "alert_sent_at",
            "spent",
            "remaining",
            "usage_pct",
            "created_at",
            "updated_at",
        ]


class BudgetCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    category_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=8, min_value=Decimal("0.00000001")
    )
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    alert_threshold = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        allow_null=True,
        required=False,
        default=None,
        min_value=Decimal("0"),
        max_value=Decimal("1"),
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["date_to"] < data["date_from"]:
            raise serializers.ValidationError(
                {"date_to": "date_to must be on or after date_from."}
            )
        return data


class BudgetUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    category_id = serializers.IntegerField(allow_null=True, required=False)
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=8, min_value=Decimal("0.00000001"), required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    alert_threshold = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        allow_null=True,
        required=False,
        min_value=Decimal("0"),
        max_value=Decimal("1"),
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        if date_from is not None and date_to is not None and date_to < date_from:
            raise serializers.ValidationError(
                {"date_to": "date_to must be on or after date_from."}
            )
        return data
