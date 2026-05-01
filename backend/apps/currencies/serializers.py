from __future__ import annotations

from rest_framework import serializers

from .models import Currency


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ("code", "name", "symbol", "decimal_places", "is_crypto")


class FxQuerySerializer(serializers.Serializer):
    base = serializers.RegexField(regex=r"^[A-Z]{3}$")
    quote = serializers.RegexField(regex=r"^[A-Z]{3}$")
    date = serializers.DateField(required=False)


class FxResponseSerializer(serializers.Serializer):
    base = serializers.CharField()
    quote = serializers.CharField()
    rate = serializers.DecimalField(max_digits=20, decimal_places=8)
    rate_date = serializers.DateField()
