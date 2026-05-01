from __future__ import annotations

import pytest

from apps.categories.models import Category
from apps.categories.selectors import build_category_tree, get_category_flat, get_visible_categories
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_category_model_exists():
    """Category model is importable and has expected fields."""
    fields = {f.name for f in Category._meta.get_fields()}
    assert "name" in fields
    assert "parent" in fields
    assert "owner" in fields
    assert "is_system" in fields
    assert "deleted_at" in fields  # from SoftDeleteModel


@pytest.mark.django_db
def test_get_visible_categories_includes_system_and_own(db):
    user = UserFactory()
    system_cat = Category.objects.create(name="Food", is_system=True, owner=None)
    own_cat = Category.objects.create(name="My Cat", is_system=False, owner=user)
    other_user = UserFactory()
    other_cat = Category.objects.create(name="Other", is_system=False, owner=other_user)

    qs = get_visible_categories(user=user)
    ids = set(qs.values_list("id", flat=True))

    assert system_cat.id in ids
    assert own_cat.id in ids
    assert other_cat.id not in ids


@pytest.mark.django_db
def test_build_category_tree_nests_children(db):
    user = UserFactory()
    parent = Category.objects.create(name="Food", is_system=True, owner=None)
    child = Category.objects.create(name="Restaurant", owner=user, parent=parent)

    qs = get_visible_categories(user=user)
    tree = build_category_tree(qs)

    parent_node = next(n for n in tree if n["id"] == parent.id)
    child_ids = [n["id"] for n in parent_node["children"]]
    assert child.id in child_ids


@pytest.mark.django_db
def test_get_category_flat_returns_list(db):
    user = UserFactory()
    Category.objects.create(name="Food", is_system=True, owner=None)
    Category.objects.create(name="My Cat", owner=user)

    result = get_category_flat(user=user)
    assert len(result) == 2
