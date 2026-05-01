from __future__ import annotations

from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "amount", "currency_code", "date", "category")
    list_filter = ("type", "currency_code")
    search_fields = ("description", "reference")
    date_hierarchy = "date"
