from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["report_type", "format", "status", "user", "requested_at", "completed_at"]
    list_filter = ["status", "report_type", "format"]
    raw_id_fields = ["user"]
    readonly_fields = ["requested_at", "completed_at"]
