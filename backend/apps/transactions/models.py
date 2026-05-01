from __future__ import annotations

from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models

from apps.categories.models import Category
from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()

INCOME = "income"
EXPENSE = "expense"
TRANSACTION_TYPE_CHOICES = [
    (INCOME, "Income"),
    (EXPENSE, "Expense"),
]


class Transaction(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency_code = models.CharField(max_length=10)
    amount_base = models.DecimalField(max_digits=20, decimal_places=8)
    base_currency = models.CharField(max_length=10)
    fx_rate_snapshot = models.DecimalField(max_digits=20, decimal_places=8)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering: ClassVar = ["-date", "-created_at"]
        indexes: ClassVar = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "type"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} {self.amount} {self.currency_code} on {self.date}"
