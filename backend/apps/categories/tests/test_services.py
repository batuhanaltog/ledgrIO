from __future__ import annotations

import pytest

from apps.categories.models import Category
from apps.categories.selectors import build_category_tree, get_category_flat, get_visible_categories
from apps.categories.services import create_category, soft_delete_category, update_category
from apps.categories.tests.factories import CategoryFactory, SystemCategoryFactory
from apps.users.tests.factories import UserFactory
from common.exceptions import (
    CategoryCycleError,
    CategoryDepthError,
    CategoryPermissionError,
)


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


@pytest.mark.django_db
def test_create_category_for_user(db):
    user = UserFactory()
    cat = create_category(user=user, name="Groceries", parent_id=None, icon="🛒", color="#4CAF50", ordering=0)
    assert cat.name == "Groceries"
    assert cat.owner == user
    assert cat.is_system is False


@pytest.mark.django_db
def test_create_category_under_system_parent(db):
    user = UserFactory()
    system = SystemCategoryFactory(name="Food")
    child = create_category(user=user, name="My Restaurant", parent_id=system.id, icon="", color="", ordering=0)
    assert child.parent == system
    assert child.owner == user


@pytest.mark.django_db
def test_create_category_cycle_raises(db):
    user = UserFactory()
    a = CategoryFactory(owner=user)
    b = CategoryFactory(owner=user, parent=a)
    c = CategoryFactory(owner=user, parent=b)
    with pytest.raises(CategoryCycleError):
        update_category(category=a, user=user, parent_id=c.id)


@pytest.mark.django_db
def test_create_category_max_depth_raises(db):
    user = UserFactory()
    parent = CategoryFactory(owner=user)
    for _ in range(9):
        parent = CategoryFactory(owner=user, parent=parent)
    # 10 levels deep already — adding one more should fail
    with pytest.raises(CategoryDepthError):
        create_category(user=user, name="Too deep", parent_id=parent.id, icon="", color="", ordering=0)


@pytest.mark.django_db
def test_update_system_category_raises(db):
    user = UserFactory()
    system = SystemCategoryFactory()
    with pytest.raises(CategoryPermissionError):
        update_category(category=system, user=user, name="Hacked")


@pytest.mark.django_db
def test_update_other_user_category_raises(db):
    user = UserFactory()
    other = UserFactory()
    other_cat = CategoryFactory(owner=other)
    with pytest.raises(CategoryPermissionError):
        update_category(category=other_cat, user=user, name="Hacked")


@pytest.mark.django_db
def test_soft_delete_system_category_raises(db):
    user = UserFactory()
    system = SystemCategoryFactory()
    with pytest.raises(CategoryPermissionError):
        soft_delete_category(category=system, user=user)


@pytest.mark.django_db
def test_soft_delete_marks_deleted_at(db):
    user = UserFactory()
    cat = CategoryFactory(owner=user)
    soft_delete_category(category=cat, user=user)
    cat.refresh_from_db()
    assert cat.deleted_at is not None
