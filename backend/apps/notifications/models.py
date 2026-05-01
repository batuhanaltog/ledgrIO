from django.db import models
from django.conf import settings
from common.models import TimestampedModel


class Notification(TimestampedModel):
    class NotificationType(models.TextChoices):
        BUDGET_ALERT = "BUDGET_ALERT", "Budget Alert"
        REPORT_READY = "REPORT_READY", "Report Ready"
        PRICE_ALERT = "PRICE_ALERT", "Price Alert"
        SYSTEM = "SYSTEM", "System"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title}"
