"""Register the daily FX fetch as a periodic task in Celery beat."""
from __future__ import annotations

import json

from django.db import migrations


def register_forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="30",
        hour="6",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )
    PeriodicTask.objects.update_or_create(
        name="currencies.fetch_daily_fx_rates [USD]",
        defaults={
            "task": "currencies.fetch_daily_fx_rates",
            "crontab": schedule,
            "kwargs": json.dumps({"base": "USD"}),
            "enabled": True,
            "description": "Fetches USD-base FX rates from Frankfurter.dev daily.",
        },
    )


def register_backwards(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="currencies.fetch_daily_fx_rates").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0002_seed_currencies"),
        ("django_celery_beat", "0018_improve_crontab_helptext"),
    ]

    operations = [
        migrations.RunPython(register_forwards, register_backwards),
    ]
