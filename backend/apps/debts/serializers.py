from __future__ import annotations

from typing import Any, ClassVar

from rest_framework import serializers

from apps.debts.models import Debt, DebtCategory, DebtPayment


class DebtCategorySerializer(serializers.ModelSerializer):
    children: serializers.SerializerMethodField = serializers.SerializerMethodField()

    class Meta:
        model = DebtCategory
        fields: ClassVar = ["id", "name", "parent_id", "children"]
        read_only_fields: ClassVar = ["id"]

    def get_children(self, obj: DebtCategory) -> list[Any]:
        children = obj.children.filter(deleted_at__isnull=True)
        return DebtCategorySerializer(children, many=True).data  # type: ignore[return-value]


class DebtCategoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    parent_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class DebtCategoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    parent_id = serializers.IntegerField(required=False, allow_null=True)


class DebtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debt
        fields: ClassVar = [
            "id",
            "name",
            "category_id",
            "original_amount",
            "current_balance",
            "expected_monthly_payment",
            "currency_code",
            "interest_rate_pct",
            "due_day",
            "is_settled",
            "notes",
            "created_at",
        ]
        read_only_fields: ClassVar = ["id", "current_balance", "is_settled", "created_at"]


class DebtCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    category_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    original_amount = serializers.DecimalField(max_digits=20, decimal_places=8)
    expected_monthly_payment = serializers.DecimalField(max_digits=20, decimal_places=8)
    currency_code = serializers.CharField(max_length=10)
    interest_rate_pct = serializers.DecimalField(
        max_digits=7, decimal_places=4, required=False, allow_null=True, default=None
    )
    due_day = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=1, max_value=31
    )
    notes = serializers.CharField(allow_blank=True, required=False, default="")


class DebtUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    expected_monthly_payment = serializers.DecimalField(
        max_digits=20, decimal_places=8, required=False
    )
    interest_rate_pct = serializers.DecimalField(
        max_digits=7, decimal_places=4, required=False, allow_null=True
    )
    due_day = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=31
    )
    notes = serializers.CharField(allow_blank=True, required=False)


class MinimalTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount_base = serializers.DecimalField(max_digits=20, decimal_places=8)
    fx_rate_snapshot = serializers.DecimalField(max_digits=20, decimal_places=8)


class MinimalDebtSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    current_balance = serializers.DecimalField(max_digits=20, decimal_places=8)
    is_settled = serializers.BooleanField()


class DebtPaymentSerializer(serializers.ModelSerializer):
    transaction = MinimalTransactionSerializer(read_only=True)
    debt = MinimalDebtSerializer(read_only=True)

    class Meta:
        model = DebtPayment
        fields: ClassVar = ["id", "amount", "paid_at", "transaction", "debt"]
        read_only_fields: ClassVar = ["id"]


class DebtPaymentCreateSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=8)
    paid_at = serializers.DateField()
    description = serializers.CharField(allow_blank=True, required=False, default="")


class ByCategorySerializer(serializers.Serializer):
    category = serializers.CharField(allow_null=True)
    expected = serializers.DecimalField(max_digits=20, decimal_places=8)
    paid = serializers.DecimalField(max_digits=20, decimal_places=8)


class DebtMonthlySummarySerializer(serializers.Serializer):
    month = serializers.CharField()
    expected_total = serializers.DecimalField(max_digits=20, decimal_places=8)
    paid_total = serializers.DecimalField(max_digits=20, decimal_places=8)
    remaining_total = serializers.DecimalField(max_digits=20, decimal_places=8)
    monthly_income = serializers.DecimalField(
        max_digits=20, decimal_places=8, allow_null=True
    )
    leftover_after_expected_debts = serializers.DecimalField(
        max_digits=20, decimal_places=8, allow_null=True
    )
    by_category = ByCategorySerializer(many=True)
