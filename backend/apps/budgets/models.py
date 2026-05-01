from django.db import models
from django.conf import settings
from common.models import TimestampedModel


class Budget(TimestampedModel):
    class Period(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey("transactions.Category", on_delete=models.CASCADE, related_name="budgets")
    amount_limit = models.DecimalField(max_digits=20, decimal_places=2)
    period = models.CharField(max_length=10, choices=Period.choices, default=Period.MONTHLY)
    alert_at_50 = models.BooleanField(default=True)
    alert_at_80 = models.BooleanField(default=True)
    alert_at_100 = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "budgets"
        ordering = ["-created_at"]
        unique_together = [["user", "category", "period"]]
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.category.name} — {self.amount_limit} ({self.period})"
