"""Register the daily recurring-template materialization as a periodic task in Celery beat."""
from __future__ import annotations

import json

from django.db import migrations


def register_forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="3",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )
    PeriodicTask.objects.update_or_create(
        name="apps.recurring.tasks.materialize_due_recurring_transactions",
        defaults={
            "task": "apps.recurring.tasks.materialize_due_recurring_transactions",
            "crontab": schedule,
            "kwargs": json.dumps({}),
            "enabled": True,
            "description": "Materializes due recurring transactions daily at 03:00 UTC.",
        },
    )


def register_backwards(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task="apps.recurring.tasks.materialize_due_recurring_transactions"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("recurring", "0001_initial"),
        ("django_celery_beat", "0018_improve_crontab_helptext"),
    ]

    operations = [
        migrations.RunPython(register_forwards, register_backwards),
    ]
