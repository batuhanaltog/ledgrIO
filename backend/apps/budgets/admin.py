from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["category", "user", "amount_limit", "period", "is_active"]
    list_filter = ["period", "is_active"]
    raw_id_fields = ["user", "category"]
