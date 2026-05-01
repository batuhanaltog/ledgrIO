from rest_framework import serializers
from .models import Portfolio


class PortfolioSerializer(serializers.ModelSerializer):
    asset_count = serializers.IntegerField(read_only=True, default=0)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, default=0)

    class Meta:
        model = Portfolio
        fields = ["id", "name", "description", "currency", "is_default", "asset_count", "total_value", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class PortfolioAllocationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    symbol = serializers.CharField()
    name = serializers.CharField()
    asset_type = serializers.CharField()
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    allocation_pct = serializers.DecimalField(max_digits=5, decimal_places=2)


class PortfolioPerformanceSerializer(serializers.Serializer):
    transaction_date = serializers.DateField()
    cumulative_value = serializers.DecimalField(max_digits=20, decimal_places=2)
