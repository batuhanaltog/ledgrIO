"""Seed the canonical currency catalog."""
from __future__ import annotations

from django.db import migrations

SEED = [
    # (code, name, symbol, decimal_places, is_crypto)
    ("TRY", "Turkish Lira", "₺", 2, False),
    ("USD", "US Dollar", "$", 2, False),
    ("EUR", "Euro", "€", 2, False),
    ("GBP", "British Pound", "£", 2, False),
    ("JPY", "Japanese Yen", "¥", 0, False),
    ("BTC", "Bitcoin", "₿", 8, True),
    ("ETH", "Ethereum", "Ξ", 8, True),
]


def seed_forwards(apps, schema_editor):
    Currency = apps.get_model("currencies", "Currency")
    for code, name, symbol, dp, is_crypto in SEED:
        Currency.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "symbol": symbol,
                "decimal_places": dp,
                "is_crypto": is_crypto,
            },
        )


def seed_backwards(apps, schema_editor):
    Currency = apps.get_model("currencies", "Currency")
    Currency.objects.filter(code__in=[row[0] for row in SEED]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_forwards, seed_backwards),
    ]
