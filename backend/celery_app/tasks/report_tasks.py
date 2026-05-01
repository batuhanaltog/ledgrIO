import os
import logging
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_report_task(self, report_id: str):
    from apps.reports.models import Report
    from apps.reports.generators import GENERATORS

    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save(update_fields=["status"])

        generator_class = GENERATORS.get(report.format)
        if not generator_class:
            raise ValueError(f"Unknown format: {report.format}")

        generator = generator_class(user=report.user, parameters=report.parameters)
        content = generator.generate()
        filename = generator.get_filename()

        media_root = os.environ.get("MEDIA_ROOT", "/app/media")
        reports_dir = os.path.join(media_root, "reports", str(report.user.id))
        os.makedirs(reports_dir, exist_ok=True)

        file_path = os.path.join(reports_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)

        report.file_path = file_path
        report.status = Report.Status.COMPLETE
        report.completed_at = timezone.now()
        report.save(update_fields=["file_path", "status", "completed_at"])

        from apps.notifications.models import Notification
        Notification.objects.create(
            user=report.user,
            notification_type=Notification.NotificationType.REPORT_READY,
            title="Report Ready",
            message=f"Your {report.report_type} report ({report.format}) is ready to download.",
            metadata={"report_id": str(report.id)},
        )

    except Exception as exc:
        logger.error("Report generation failed for %s: %s", report_id, exc)
        try:
            report = Report.objects.get(id=report_id)
            report.status = Report.Status.FAILED
            report.error_message = str(exc)
            report.save(update_fields=["status", "error_message"])
        except Report.DoesNotExist:
            pass
        raise self.retry(exc=exc, countdown=60)
