from rest_framework import serializers
from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id", "category", "category_name", "amount_limit", "period",
            "alert_at_50", "alert_at_80", "alert_at_100", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate_category(self, value):
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Category not found.")
        return value
