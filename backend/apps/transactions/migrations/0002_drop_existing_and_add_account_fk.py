from django.db import migrations, models
import django.db.models.deletion


def delete_all_transactions(apps, schema_editor):
    Transaction = apps.get_model("transactions", "Transaction")
    Transaction.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_all_transactions, migrations.RunPython.noop),
        migrations.AddField(
            model_name="transaction",
            name="account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="accounts.account",
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["account", "date"], name="transaction_account_id_date_idx"),
        ),
    ]
