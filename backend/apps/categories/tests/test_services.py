from __future__ import annotations

import pytest

from apps.categories.models import Category


@pytest.mark.django_db
def test_category_model_exists():
    """Category model is importable and has expected fields."""
    fields = {f.name for f in Category._meta.get_fields()}
    assert "name" in fields
    assert "parent" in fields
    assert "owner" in fields
    assert "is_system" in fields
    assert "deleted_at" in fields  # from SoftDeleteModel
