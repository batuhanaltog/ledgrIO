from __future__ import annotations

from django.contrib import admin

from apps.recurring.models import RecurringTemplate


@admin.register(RecurringTemplate)
class RecurringTemplateAdmin(admin.ModelAdmin):
    list_display = ["description", "frequency", "is_active", "user", "account"]  # noqa: RUF012
    list_filter = ["frequency", "is_active"]  # noqa: RUF012
    search_fields = ["description"]  # noqa: RUF012
