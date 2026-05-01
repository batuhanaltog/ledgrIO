from django.db import models
from django.conf import settings
from common.models import TimestampedModel


class Report(TimestampedModel):
    class ReportType(models.TextChoices):
        PORTFOLIO_SUMMARY = "PORTFOLIO_SUMMARY", "Portfolio Summary"
        TRANSACTION_HISTORY = "TRANSACTION_HISTORY", "Transaction History"
        BUDGET_ANALYSIS = "BUDGET_ANALYSIS", "Budget Analysis"
        FULL_EXPORT = "FULL_EXPORT", "Full Export"

    class Format(models.TextChoices):
        CSV = "CSV", "CSV"
        PDF = "PDF", "PDF"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETE = "COMPLETE", "Complete"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    format = models.CharField(max_length=3, choices=Format.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    parameters = models.JSONField(default=dict)
    file_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reports"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.report_type} ({self.format}) — {self.status}"
