from __future__ import annotations

from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

User = get_user_model()


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="budgets",
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    date_from = models.DateField()
    date_to = models.DateField()
    alert_threshold = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )
    alert_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="budget_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(date_to__gte=models.F("date_from")),
                name="budget_date_to_gte_date_from",
            ),
            models.CheckConstraint(
                check=(
                    Q(alert_threshold__isnull=True)
                    | Q(alert_threshold__gte=0, alert_threshold__lte=1)
                ),
                name="budget_alert_threshold_valid_range",
            ),
        ]
        indexes: ClassVar = [
            models.Index(fields=["user", "date_from", "date_to"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.amount})"
