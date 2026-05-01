import decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("transactions", "0002_drop_existing_and_add_account_fk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DebtCategory",
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
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="debt_categories",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="children",
                        to="debts.debtcategory",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "all_objects",
            },
        ),
        migrations.CreateModel(
            name="Debt",
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
                ("name", models.CharField(max_length=200)),
                (
                    "original_amount",
                    models.DecimalField(decimal_places=8, max_digits=20),
                ),
                (
                    "current_balance",
                    models.DecimalField(decimal_places=8, max_digits=20),
                ),
                (
                    "expected_monthly_payment",
                    models.DecimalField(decimal_places=8, max_digits=20),
                ),
                ("currency_code", models.CharField(max_length=10)),
                (
                    "interest_rate_pct",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=7, null=True
                    ),
                ),
                ("due_day", models.SmallIntegerField(blank=True, null=True)),
                ("is_settled", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="debts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="debts",
                        to="debts.debtcategory",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "all_objects",
            },
        ),
        migrations.CreateModel(
            name="DebtPayment",
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
                    "amount",
                    models.DecimalField(decimal_places=8, max_digits=20),
                ),
                ("paid_at", models.DateField(db_index=True)),
                (
                    "debt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="debts.debt",
                    ),
                ),
                (
                    "transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="debt_payment",
                        to="transactions.transaction",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="debtcategory",
            index=models.Index(
                fields=["user", "parent"],
                name="debts_debtc_user_id_parent_id_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="debtcategory",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True),
                fields=["user", "parent", "name"],
                name="debtcat_user_parent_name_unique_alive",
            ),
        ),
        migrations.AddIndex(
            model_name="debt",
            index=models.Index(
                fields=["user", "is_settled"],
                name="debts_debt_user_id_is_settled_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="debt",
            index=models.Index(
                fields=["user", "category"],
                name="debts_debt_user_id_category_id_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="debt",
            constraint=models.CheckConstraint(
                check=models.Q(original_amount__gt=decimal.Decimal("0")),
                name="debt_original_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="debt",
            constraint=models.CheckConstraint(
                check=models.Q(current_balance__gte=decimal.Decimal("0")),
                name="debt_current_balance_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="debt",
            constraint=models.CheckConstraint(
                check=models.Q(expected_monthly_payment__gte=decimal.Decimal("0")),
                name="debt_expected_payment_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="debt",
            constraint=models.CheckConstraint(
                check=models.Q(due_day__isnull=True)
                | (models.Q(due_day__gte=1) & models.Q(due_day__lte=31)),
                name="debt_due_day_range",
            ),
        ),
        migrations.AddIndex(
            model_name="debtpayment",
            index=models.Index(
                fields=["debt", "paid_at"],
                name="debts_debtpayment_debt_id_paid_at_idx",
            ),
        ),
    ]
