from django.contrib import admin
from .models import Portfolio


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "currency", "is_default", "created_at"]
    list_filter = ["currency", "is_default"]
    search_fields = ["name", "user__email"]
    raw_id_fields = ["user"]
