from rest_framework import serializers
from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    unrealized_pnl = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id", "portfolio", "name", "symbol", "asset_type",
            "quantity", "average_cost", "current_price", "currency",
            "current_value", "unrealized_pnl", "last_price_update",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_price_update"]

    def validate_portfolio(self, value):
        if value.user != self.context["request"].user:
            raise serializers.ValidationError("Portfolio not found.")
        return value
