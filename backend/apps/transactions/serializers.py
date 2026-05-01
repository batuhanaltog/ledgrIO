from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from rest_framework import serializers

from apps.transactions.models import EXPENSE, INCOME, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields: ClassVar = [
            "id",
            "type",
            "amount",
            "currency_code",
            "amount_base",
            "base_currency",
            "fx_rate_snapshot",
            "category",
            "date",
            "description",
            "reference",
            "created_at",
        ]

    def get_category(self, obj: Transaction) -> dict | None:
        if obj.category is None:
            return None
        cat = obj.category
        parent = cat.parent
        return {
            "id": cat.id,
            "name": cat.name,
            "color": cat.color,
            "icon": cat.icon,
            "parent_name": parent.name if parent is not None else None,
        }


class TransactionWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[INCOME, EXPENSE])
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, min_value=Decimal("0.00000001"))
    currency_code = serializers.CharField(max_length=10)
    category_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    date = serializers.DateField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    reference = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")


class TransactionFilterSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[INCOME, EXPENSE], required=False)
    category = serializers.IntegerField(required=False)
    currency = serializers.CharField(max_length=10, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    amount_min = serializers.DecimalField(max_digits=20, decimal_places=8, required=False)
    amount_max = serializers.DecimalField(max_digits=20, decimal_places=8, required=False)
    search = serializers.CharField(max_length=200, required=False)
    ordering = serializers.CharField(max_length=20, required=False)


class TransactionSummaryQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    group_by = serializers.ChoiceField(choices=["day", "week", "month"], required=False, default="day")
