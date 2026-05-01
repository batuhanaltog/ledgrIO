from django.contrib import admin

from apps.recurring.models import RecurringTemplate


@admin.register(RecurringTemplate)
class RecurringTemplateAdmin(admin.ModelAdmin):
    list_display = ["description", "frequency", "is_active", "user", "account"]
    list_filter = ["frequency", "is_active"]
    search_fields = ["description"]
