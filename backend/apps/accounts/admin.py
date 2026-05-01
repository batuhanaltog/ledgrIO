from __future__ import annotations

from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "account_type", "currency_code", "is_active", "user"]
    list_filter = ["account_type", "is_active"]
    search_fields = ["name", "user__email"]
