from __future__ import annotations

from django.db import migrations


SYSTEM_CATEGORIES = [
    {"name": "Food & Drink", "icon": "🍔", "color": "#FF9800", "ordering": 1},
    {"name": "Transport", "icon": "🚗", "color": "#2196F3", "ordering": 2},
    {"name": "Health", "icon": "🏥", "color": "#4CAF50", "ordering": 3},
    {"name": "Entertainment", "icon": "🎬", "color": "#9C27B0", "ordering": 4},
    {"name": "Shopping", "icon": "🛍️", "color": "#F44336", "ordering": 5},
    {"name": "Other", "icon": "📦", "color": "#607D8B", "ordering": 6},
    {"name": "Income", "icon": "💰", "color": "#4CAF50", "ordering": 0},
]


def seed_system_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    for data in SYSTEM_CATEGORIES:
        Category.objects.get_or_create(
            name=data["name"],
            is_system=True,
            defaults={
                "icon": data["icon"],
                "color": data["color"],
                "ordering": data["ordering"],
                "owner": None,
            },
        )


def unseed_system_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_system_categories, reverse_code=unseed_system_categories),
    ]
