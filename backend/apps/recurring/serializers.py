from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

from rest_framework import serializers

from apps.recurring.models import RECURRING_FREQUENCY_CHOICES, RecurringTemplate
from apps.transactions.models import EXPENSE, INCOME


class RecurringTemplateSerializer(serializers.ModelSerializer):
    next_due_date = serializers.SerializerMethodField()
    recent_generated = serializers.SerializerMethodField()

    class Meta:
        model = RecurringTemplate
        fields: ClassVar = [
            "id",
            "type",
            "amount",
            "currency_code",
            "account",
            "category",
            "description",
            "frequency",
            "day_of_period",
            "start_date",
            "end_date",
            "last_generated_date",
            "is_active",
            "created_at",
            "next_due_date",
            "recent_generated",
        ]
        read_only_fields: ClassVar = [
            "id",
            "created_at",
            "last_generated_date",
            "next_due_date",
            "recent_generated",
        ]

    def get_next_due_date(self, obj: RecurringTemplate) -> date | None:
        from apps.recurring.services import compute_next_due_date

        return compute_next_due_date(template=obj)

    def get_recent_generated(self, obj: RecurringTemplate) -> list[dict[str, Any]]:
        from apps.transactions.models import Transaction

        if obj.last_generated_date is None:
            return []

        txns = (
            Transaction.objects.filter(
                user=obj.user,
                description=obj.description,
                currency_code=obj.currency_code,
                type=obj.type,
            )
            .order_by("-date", "-created_at")[:5]
        )
        return [
            {"id": t.pk, "date": t.date, "amount": t.amount}
            for t in txns
        ]


class RecurringTemplateListSerializer(serializers.ModelSerializer):
    next_due_date = serializers.SerializerMethodField()

    class Meta:
        model = RecurringTemplate
        fields: ClassVar = [
            "id",
            "type",
            "amount",
            "currency_code",
            "account",
            "category",
            "description",
            "frequency",
            "day_of_period",
            "start_date",
            "end_date",
            "last_generated_date",
            "is_active",
            "created_at",
            "next_due_date",
        ]
        read_only_fields: ClassVar = [
            "id",
            "created_at",
            "last_generated_date",
            "next_due_date",
        ]

    def get_next_due_date(self, obj: RecurringTemplate) -> date | None:
        from apps.recurring.services import compute_next_due_date

        return compute_next_due_date(template=obj)


class RecurringTemplateCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[INCOME, EXPENSE])
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
    )
    currency_code = serializers.CharField(max_length=10)
    account_id = serializers.IntegerField()
    category_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    description = serializers.CharField(max_length=255)
    frequency = serializers.ChoiceField(choices=[f[0] for f in RECURRING_FREQUENCY_CHOICES])
    day_of_period = serializers.IntegerField(min_value=1, max_value=366)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        frequency = data.get("frequency")
        day = data.get("day_of_period")
        if frequency == "weekly" and day is not None and not (1 <= day <= 7):
            raise serializers.ValidationError(
                {"day_of_period": "For weekly frequency, day_of_period must be 1–7."}
            )
        if frequency == "monthly" and day is not None and not (1 <= day <= 31):
            raise serializers.ValidationError(
                {"day_of_period": "For monthly frequency, day_of_period must be 1–31."}
            )
        end_date = data.get("end_date")
        start_date = data.get("start_date")
        if end_date is not None and start_date is not None and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "end_date must be on or after start_date."}
            )
        return data


class RecurringTemplateUpdateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[INCOME, EXPENSE], required=False)
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
        required=False,
    )
    currency_code = serializers.CharField(max_length=10, required=False)
    account_id = serializers.IntegerField(required=False)
    category_id = serializers.IntegerField(allow_null=True, required=False)
    description = serializers.CharField(max_length=255, required=False)
    frequency = serializers.ChoiceField(
        choices=[f[0] for f in RECURRING_FREQUENCY_CHOICES], required=False
    )
    day_of_period = serializers.IntegerField(min_value=1, max_value=366, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
