from django.db import models
from django.conf import settings
from common.models import TimestampedModel


class Category(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="categories", null=True, blank=True
    )
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True, default="#6366f1")
    is_income = models.BooleanField(default=False)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        unique_together = [["user", "name"]]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Transaction(TimestampedModel):
    class TransactionType(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
        DIVIDEND = "DIVIDEND", "Dividend"
        EXPENSE = "EXPENSE", "Expense"
        INCOME = "INCOME", "Income"
        TRANSFER = "TRANSFER", "Transfer"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    portfolio = models.ForeignKey(
        "portfolios.Portfolio", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="transactions"
    )
    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="transactions"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    quantity = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    currency = models.CharField(max_length=3, default="USD")
    notes = models.TextField(blank=True)
    transaction_date = models.DateField()

    class Meta:
        db_table = "transactions"
        ordering = ["-transaction_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "transaction_date"]),
            models.Index(fields=["portfolio", "transaction_date"]),
            models.Index(fields=["category"]),
            models.Index(fields=["asset"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} {self.currency} on {self.transaction_date}"
