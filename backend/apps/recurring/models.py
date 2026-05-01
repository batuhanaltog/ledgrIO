from __future__ import annotations

from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

from apps.transactions.models import TRANSACTION_TYPE_CHOICES
from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()

RECURRING_FREQUENCY_CHOICES = [
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
]


class RecurringTemplate(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_templates")
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency_code = models.CharField(max_length=10)
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="recurring_templates",
    )
    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recurring_templates",
    )
    description = models.CharField(max_length=255)
    frequency = models.CharField(max_length=10, choices=RECURRING_FREQUENCY_CHOICES)
    day_of_period = models.SmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    last_generated_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="recurring_amount_positive",
            ),
            models.CheckConstraint(
                check=(
                    Q(frequency="weekly", day_of_period__gte=1, day_of_period__lte=7)
                    | Q(frequency="monthly", day_of_period__gte=1, day_of_period__lte=31)
                    | Q(frequency="yearly", day_of_period__gte=1, day_of_period__lte=366)
                ),
                name="recurring_day_of_period_valid_for_frequency",
            ),
            models.CheckConstraint(
                check=(
                    Q(end_date__isnull=True)
                    | Q(end_date__gte=models.F("start_date"))
                ),
                name="recurring_end_date_after_start",
            ),
        ]
        indexes: ClassVar = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["last_generated_date", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.description} ({self.frequency})"
