from __future__ import annotations

from django.contrib import admin

from .models import Currency, FxRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "decimal_places", "is_crypto")
    list_filter = ("is_crypto",)
    search_fields = ("code", "name")


@admin.register(FxRate)
class FxRateAdmin(admin.ModelAdmin):
    list_display = ("base_code", "quote_code", "rate", "rate_date", "fetched_at")
    list_filter = ("base_code", "quote_code")
    date_hierarchy = "rate_date"
