from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()

ACCOUNT_TYPE_CHOICES = [
    ("cash", "Cash"),
    ("bank", "Bank"),
    ("credit_card", "Credit Card"),
    ("savings", "Savings"),
]


class Account(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    currency_code = models.CharField(max_length=10)
    opening_balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=Decimal("0")
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["user", "name"],
                condition=Q(deleted_at__isnull=True),
                name="account_user_name_unique_alive",
            ),
        ]
        ordering: ClassVar = ["name"]
        indexes: ClassVar = [
            models.Index(fields=["user", "account_type"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency_code})"
