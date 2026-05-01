"""Register the daily budget alert task as a periodic task in Celery beat."""
from __future__ import annotations

import json

from django.db import migrations


def register_forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="7",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )
    PeriodicTask.objects.update_or_create(
        name="apps.budgets.tasks.send_budget_alerts",
        defaults={
            "task": "apps.budgets.tasks.send_budget_alerts",
            "crontab": schedule,
            "kwargs": json.dumps({}),
            "enabled": True,
            "description": "Sends budget threshold alert emails daily at 07:00 UTC.",
        },
    )


def register_backwards(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task="apps.budgets.tasks.send_budget_alerts"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("budgets", "0001_initial"),
        ("django_celery_beat", "0018_improve_crontab_helptext"),
    ]

    operations = [
        migrations.RunPython(register_forwards, register_backwards),
    ]
