from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser

from common.exceptions import (
    CategoryCycleError,
    CategoryDepthError,
    CategoryPermissionError,
)

from .models import MAX_CATEGORY_DEPTH, Category


def _check_no_cycle(*, category_id: int | None, new_parent_id: int) -> None:
    """Walk the parent chain from new_parent_id; raise if category_id is encountered."""
    if category_id is None:
        return
    current_id: int | None = new_parent_id
    while current_id is not None:
        if current_id == category_id:
            raise CategoryCycleError("Setting this parent would create a cycle.")
        try:
            current_id = Category.objects.values_list("parent_id", flat=True).get(id=current_id)
        except Category.DoesNotExist:
            break


def _measure_depth(parent_id: int | None) -> int:
    """Return depth of a node that would have parent_id as its parent (1-based)."""
    depth = 1
    current_id = parent_id
    while current_id is not None:
        depth += 1
        try:
            current_id = Category.objects.values_list("parent_id", flat=True).get(id=current_id)
        except Category.DoesNotExist:
            break
    return depth


def create_category(
    *,
    user: AbstractBaseUser,
    name: str,
    parent_id: int | None,
    icon: str = "",
    color: str = "",
    ordering: int = 0,
) -> Category:
    if parent_id is not None:
        depth = _measure_depth(parent_id)
        if depth >= MAX_CATEGORY_DEPTH:
            raise CategoryDepthError(f"Maximum category depth ({MAX_CATEGORY_DEPTH}) exceeded.")

    cat: Category = Category.objects.create(
        name=name,
        parent_id=parent_id,
        owner=user,
        is_system=False,
        icon=icon,
        color=color,
        ordering=ordering,
    )
    return cat


def update_category(
    *,
    category: Category,
    user: AbstractBaseUser,
    **fields: Any,
) -> Category:
    if category.is_system:
        raise CategoryPermissionError("System categories cannot be modified.")
    if category.owner_id != user.pk:
        raise CategoryPermissionError("You do not own this category.")

    if "parent_id" in fields and fields["parent_id"] is not None:
        new_parent_id: int = fields["parent_id"]
        _check_no_cycle(category_id=category.id, new_parent_id=new_parent_id)
        depth = _measure_depth(new_parent_id)
        if depth >= MAX_CATEGORY_DEPTH:
            raise CategoryDepthError(f"Maximum category depth ({MAX_CATEGORY_DEPTH}) exceeded.")

    for attr, value in fields.items():
        setattr(category, attr, value)
    category.save()
    return category


def soft_delete_category(*, category: Category, user: AbstractBaseUser) -> None:
    if category.is_system:
        raise CategoryPermissionError("System categories cannot be deleted.")
    if category.owner_id != user.pk:
        raise CategoryPermissionError("You do not own this category.")
    category.soft_delete()
