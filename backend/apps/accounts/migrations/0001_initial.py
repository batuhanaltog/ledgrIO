import decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Account",
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
                ("name", models.CharField(max_length=100)),
                (
                    "account_type",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("bank", "Bank"),
                            ("credit_card", "Credit Card"),
                            ("savings", "Savings"),
                        ],
                        max_length=20,
                    ),
                ),
                ("currency_code", models.CharField(max_length=10)),
                (
                    "opening_balance",
                    models.DecimalField(
                        decimal_places=8,
                        default=decimal.Decimal("0"),
                        max_digits=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "all_objects",
            },
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["user", "account_type"], name="accounts_ac_user_id_account_type_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["user", "is_active"], name="accounts_ac_user_id_is_active_idx"),
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True),
                fields=["user", "name"],
                name="account_user_name_unique_alive",
            ),
        ),
    ]
