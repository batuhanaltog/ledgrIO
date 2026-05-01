from django.contrib import admin

from apps.debts.models import Debt, DebtCategory, DebtPayment


@admin.register(DebtCategory)
class DebtCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "parent", "deleted_at", "created_at")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "currency_code",
        "original_amount",
        "current_balance",
        "expected_monthly_payment",
        "is_settled",
        "deleted_at",
        "created_at",
    )
    list_filter = ("user", "is_settled", "currency_code")
    search_fields = ("name",)


@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ("debt", "amount", "paid_at", "transaction", "created_at")
    list_filter = ("paid_at",)
    search_fields = ("debt__name",)
