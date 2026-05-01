from rest_framework import serializers
from .models import Transaction, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "icon", "color", "is_income", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "portfolio", "asset", "category", "category_name",
            "transaction_type", "amount", "quantity", "price_per_unit",
            "fee", "currency", "notes", "transaction_date",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def validate(self, attrs):
        portfolio = attrs.get("portfolio")
        if portfolio and portfolio.user != self.context["request"].user:
            raise serializers.ValidationError({"portfolio": "Portfolio not found."})
        return attrs


class TransactionListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = ["id", "transaction_type", "amount", "currency", "category_name", "transaction_date"]
