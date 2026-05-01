from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()


class DebtCategory(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="debt_categories")
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["user", "parent", "name"],
                condition=Q(deleted_at__isnull=True),
                name="debtcat_user_parent_name_unique_alive",
            ),
        ]
        indexes: ClassVar = [
            models.Index(fields=["user", "parent"]),
        ]

    def __str__(self) -> str:
        return self.name


class Debt(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="debts")
    category = models.ForeignKey(
        DebtCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="debts",
    )
    name = models.CharField(max_length=200)
    original_amount = models.DecimalField(max_digits=20, decimal_places=8)
    current_balance = models.DecimalField(max_digits=20, decimal_places=8)
    expected_monthly_payment = models.DecimalField(max_digits=20, decimal_places=8)
    currency_code = models.CharField(max_length=10)
    interest_rate_pct = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    due_day = models.SmallIntegerField(null=True, blank=True)
    is_settled = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(
                check=Q(original_amount__gt=Decimal("0")),
                name="debt_original_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(current_balance__gte=Decimal("0")),
                name="debt_current_balance_non_negative",
            ),
            models.CheckConstraint(
                check=Q(expected_monthly_payment__gte=Decimal("0")),
                name="debt_expected_payment_non_negative",
            ),
            models.CheckConstraint(
                check=Q(due_day__isnull=True) | (Q(due_day__gte=1) & Q(due_day__lte=31)),
                name="debt_due_day_range",
            ),
        ]
        indexes: ClassVar = [
            models.Index(fields=["user", "is_settled"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency_code})"


class DebtPayment(TimestampedModel):
    debt = models.ForeignKey(Debt, on_delete=models.PROTECT, related_name="payments")
    transaction = models.OneToOneField(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        related_name="debt_payment",
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    paid_at = models.DateField(db_index=True)

    class Meta:
        indexes: ClassVar = [
            models.Index(fields=["debt", "paid_at"]),
        ]

    def __str__(self) -> str:
        return f"Payment {self.amount} on {self.paid_at}"
