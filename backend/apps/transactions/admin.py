from django.contrib import admin
from .models import Transaction, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_income", "color"]
    list_filter = ["is_income"]
    search_fields = ["name"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["transaction_type", "amount", "currency", "transaction_date", "user", "category"]
    list_filter = ["transaction_type", "currency"]
    search_fields = ["notes", "user__email"]
    date_hierarchy = "transaction_date"
    raw_id_fields = ["user", "portfolio", "asset", "category"]
