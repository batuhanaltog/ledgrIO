from __future__ import annotations

import django.db.models.deletion
import django.db.models.expressions
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("categories", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecurringTemplate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("income", "Income"), ("expense", "Expense")],
                        max_length=10,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=8, max_digits=20)),
                ("currency_code", models.CharField(max_length=10)),
                ("description", models.CharField(max_length=255)),
                (
                    "frequency",
                    models.CharField(
                        choices=[
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                            ("yearly", "Yearly"),
                        ],
                        max_length=10,
                    ),
                ),
                ("day_of_period", models.SmallIntegerField()),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("last_generated_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recurring_templates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recurring_templates",
                        to="accounts.account",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recurring_templates",
                        to="categories.category",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "all_objects",
            },
        ),
        migrations.AddIndex(
            model_name="recurringtemplate",
            index=models.Index(
                fields=["user", "is_active"],
                name="recurring_r_user_id_is_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="recurringtemplate",
            index=models.Index(
                fields=["last_generated_date", "is_active"],
                name="recurring_r_last_ge_is_active_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="recurringtemplate",
            constraint=models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="recurring_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="recurringtemplate",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(
                        frequency="weekly",
                        day_of_period__gte=1,
                        day_of_period__lte=7,
                    )
                    | models.Q(
                        frequency="monthly",
                        day_of_period__gte=1,
                        day_of_period__lte=31,
                    )
                    | models.Q(
                        frequency="yearly",
                        day_of_period__gte=1,
                        day_of_period__lte=366,
                    )
                ),
                name="recurring_day_of_period_valid_for_frequency",
            ),
        ),
        migrations.AddConstraint(
            model_name="recurringtemplate",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(end_date__isnull=True)
                    | models.Q(
                        end_date__gte=django.db.models.expressions.F("start_date")
                    )
                ),
                name="recurring_end_date_after_start",
            ),
        ),
    ]
