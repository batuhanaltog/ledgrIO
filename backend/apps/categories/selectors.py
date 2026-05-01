from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models

from .models import Category

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


def get_visible_categories(*, user: AbstractBaseUser) -> models.QuerySet[Category]:
    """Return system categories plus the user's own categories (alive only)."""
    return Category.objects.filter(  # type: ignore[no-any-return]
        models.Q(is_system=True) | models.Q(owner=user)
    ).select_related("parent").order_by("is_system", "ordering", "name")


def build_category_tree(qs: models.QuerySet[Category]) -> list[dict[str, Any]]:
    """Convert a flat category queryset into a nested tree (system categories first)."""
    categories = list(qs)
    nodes: dict[int, dict[str, Any]] = {}
    for cat in categories:
        nodes[cat.id] = {
            "id": cat.id,
            "name": cat.name,
            "icon": cat.icon,
            "color": cat.color,
            "is_system": cat.is_system,
            "owner_id": cat.owner_id,
            "ordering": cat.ordering,
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for cat in categories:
        node = nodes[cat.id]
        if cat.parent_id and cat.parent_id in nodes:
            nodes[cat.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


def get_category_flat(*, user: AbstractBaseUser) -> list[dict[str, Any]]:
    """Return visible categories as a flat list (for dropdowns)."""
    qs = get_visible_categories(user=user)
    return [dict(row) for row in qs.values("id", "name", "icon", "color", "is_system", "owner_id", "parent_id", "ordering")]
