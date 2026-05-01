# Phase 4: Transactions + Categories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `apps/categories/` and `apps/transactions/` — income/expense tracking with unlimited category hierarchy, multi-currency FX snapshot, and comprehensive reporting.

**Architecture:** Two Django apps (`categories` → `transactions` dependency direction). Service pattern: models hold data, services own all writes, selectors own all reads, views handle HTTP only. Categories support unlimited self-referential hierarchy with system/user-owned distinction. Transactions store FX rate snapshot at write time; historical records are immutable to exchange rate fluctuations.

**Tech Stack:** Django 5, DRF, PostgreSQL 16, factory-boy, pytest. No new dependencies needed.

---

## File Map

### New files
| File | Responsibility |
|------|---------------|
| `backend/apps/categories/__init__.py` | App package |
| `backend/apps/categories/apps.py` | AppConfig |
| `backend/apps/categories/models.py` | Category model (self-ref FK, SoftDeleteModel) |
| `backend/apps/categories/services.py` | create / update / soft_delete category |
| `backend/apps/categories/selectors.py` | get_visible_categories, build_category_tree, get_category_flat |
| `backend/apps/categories/serializers.py` | CategoryFlatSerializer, CategoryWriteSerializer |
| `backend/apps/categories/views.py` | CategoryListView, CategoryDetailView |
| `backend/apps/categories/urls.py` | URL patterns |
| `backend/apps/categories/admin.py` | Admin registration |
| `backend/apps/categories/migrations/0001_initial.py` | Category model + indexes |
| `backend/apps/categories/migrations/0002_seed_system_categories.py` | 6 system categories |
| `backend/apps/categories/tests/__init__.py` | Test package |
| `backend/apps/categories/tests/factories.py` | CategoryFactory, SystemCategoryFactory |
| `backend/apps/categories/tests/test_services.py` | Service unit tests |
| `backend/apps/categories/tests/test_views.py` | API endpoint tests |
| `backend/apps/transactions/__init__.py` | App package |
| `backend/apps/transactions/apps.py` | AppConfig |
| `backend/apps/transactions/models.py` | Transaction model (FX snapshot, SoftDeleteModel) |
| `backend/apps/transactions/services.py` | create / update / soft_delete transaction |
| `backend/apps/transactions/selectors.py` | get_transaction_list (filters), get_transaction_summary |
| `backend/apps/transactions/serializers.py` | TransactionSerializer, TransactionWriteSerializer, etc. |
| `backend/apps/transactions/views.py` | TransactionListView, TransactionDetailView, TransactionSummaryView |
| `backend/apps/transactions/urls.py` | URL patterns |
| `backend/apps/transactions/admin.py` | Admin registration |
| `backend/apps/transactions/migrations/0001_initial.py` | Transaction model + composite indexes |
| `backend/apps/transactions/tests/__init__.py` | Test package |
| `backend/apps/transactions/tests/factories.py` | TransactionFactory |
| `backend/apps/transactions/tests/test_services.py` | FX snapshot logic, update rules |
| `backend/apps/transactions/tests/test_views.py` | List filters, summary endpoint |

### Modified files
| File | Change |
|------|--------|
| `backend/config/settings/base.py` | Add `apps.categories`, `apps.transactions` to LOCAL_APPS |
| `backend/config/urls.py` | Include categories and transactions URL patterns |
| `backend/common/exceptions.py` | Add 5 new exception classes |
| `backend/apps/currencies/services.py` | Add public `get_exchange_rate()` function |
| `backend/CLAUDE.md` | Update Phase 4 status |

---

## Task 1: App Scaffolding + INSTALLED_APPS

**Files:**
- Create: `backend/apps/categories/__init__.py`, `apps.py`, `admin.py`, `tests/__init__.py`
- Create: `backend/apps/transactions/__init__.py`, `apps.py`, `admin.py`, `tests/__init__.py`
- Modify: `backend/config/settings/base.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/apps/categories/migrations
mkdir -p backend/apps/categories/tests
mkdir -p backend/apps/transactions/migrations
mkdir -p backend/apps/transactions/tests
touch backend/apps/categories/__init__.py
touch backend/apps/categories/migrations/__init__.py
touch backend/apps/categories/tests/__init__.py
touch backend/apps/transactions/__init__.py
touch backend/apps/transactions/migrations/__init__.py
touch backend/apps/transactions/tests/__init__.py
```

- [ ] **Step 2: Write `backend/apps/categories/apps.py`**

```python
from django.apps import AppConfig


class CategoriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.categories"
    verbose_name = "Categories"
```

- [ ] **Step 3: Write `backend/apps/transactions/apps.py`**

```python
from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transactions"
    verbose_name = "Transactions"
```

- [ ] **Step 4: Write stub admin files**

`backend/apps/categories/admin.py`:
```python
from django.contrib import admin
```

`backend/apps/transactions/admin.py`:
```python
from django.contrib import admin
```

- [ ] **Step 5: Register apps in INSTALLED_APPS**

In `backend/config/settings/base.py`, find `LOCAL_APPS` and add two entries:

```python
LOCAL_APPS: Final[list[str]] = [
    "common",
    "apps.users",
    "apps.currencies",
    "apps.categories",
    "apps.transactions",
]
```

- [ ] **Step 6: Verify Django recognizes apps**

```bash
docker compose exec backend python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 7: Commit**

```bash
git add backend/apps/categories/ backend/apps/transactions/ backend/config/settings/base.py
git commit -m "chore(phase4): scaffold categories and transactions app structure"
```

---

## Task 2: Common Exceptions

**Files:**
- Modify: `backend/common/exceptions.py`

- [ ] **Step 1: Add 5 new exception classes to `common/exceptions.py`**

Append after the existing imports and before `_TYPE_BY_STATUS`:

```python
class CategoryNotFoundError(LookupError):
    """Requested category does not exist or is not visible to the user."""


class CategoryPermissionError(PermissionError):
    """User attempted to modify a system category or another user's category."""


class CategoryCycleError(ValueError):
    """Setting this parent would create a cycle in the category tree."""


class CategoryDepthError(ValueError):
    """Category hierarchy would exceed the maximum allowed depth (10)."""


class TransactionNotFoundError(LookupError):
    """Requested transaction does not exist or belongs to another user."""
```

- [ ] **Step 2: Verify import works**

```bash
docker compose exec backend python manage.py shell -c "from common.exceptions import CategoryNotFoundError, TransactionNotFoundError; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/common/exceptions.py
git commit -m "feat(exceptions): add category and transaction exception classes"
```

---

## Task 3: Category Model + Migration

**Files:**
- Create: `backend/apps/categories/models.py`
- Create: `backend/apps/categories/migrations/0001_initial.py` (via makemigrations)

- [ ] **Step 1: Write failing test for model existence**

Create `backend/apps/categories/tests/test_services.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py::test_category_model_exists -v
```

Expected: `ImportError` or `ModuleNotFoundError` — model doesn't exist yet.

- [ ] **Step 3: Write `backend/apps/categories/models.py`**

```python
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models

from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()

MAX_CATEGORY_DEPTH = 10


class Category(TimestampedModel, SoftDeleteModel):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    is_system = models.BooleanField(default=False)
    ordering = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["is_system"]),
        ]

    def __str__(self) -> str:
        return self.name
```

- [ ] **Step 4: Generate migration**

```bash
docker compose exec backend python manage.py makemigrations categories --name initial
```

Expected: `Migrations for 'categories': apps/categories/migrations/0001_initial.py`

- [ ] **Step 5: Run migration**

```bash
docker compose exec backend python manage.py migrate
```

Expected: `Applying categories.0001_initial... OK`

- [ ] **Step 6: Run test to verify it passes**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py::test_category_model_exists -v
```

Expected: `PASSED`

- [ ] **Step 7: Register in admin**

Update `backend/apps/categories/admin.py`:

```python
from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "is_system", "owner", "parent", "ordering"]
    list_filter = ["is_system"]
    search_fields = ["name"]
```

- [ ] **Step 8: Commit**

```bash
git add backend/apps/categories/
git commit -m "feat(categories): add Category model and migration"
```

---

## Task 4: Category Selectors

**Files:**
- Create: `backend/apps/categories/selectors.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/apps/categories/tests/test_services.py`:

```python
from apps.categories.selectors import build_category_tree, get_category_flat, get_visible_categories
from apps.users.tests.factories import UserFactory


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

    # Find parent node
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py -k "selector or visible or tree or flat" -v
```

Expected: `ImportError` — selectors module doesn't exist yet.

- [ ] **Step 3: Write `backend/apps/categories/selectors.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .models import Category

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.db.models import QuerySet


def get_visible_categories(*, user: "AbstractBaseUser") -> "QuerySet[Category]":
    """Return system categories plus the user's own categories (alive only)."""
    return Category.objects.filter(
        models.Q(is_system=True) | models.Q(owner=user)
    ).select_related("parent").order_by("is_system", "ordering", "name")


def build_category_tree(qs: "QuerySet[Category]") -> list[dict]:
    """Convert a flat category queryset into a nested tree (system categories first)."""
    categories = list(qs)
    nodes: dict[int, dict] = {}
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

    roots: list[dict] = []
    for cat in categories:
        node = nodes[cat.id]
        if cat.parent_id and cat.parent_id in nodes:
            nodes[cat.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


def get_category_flat(*, user: "AbstractBaseUser") -> list[dict]:
    """Return visible categories as a flat list (for dropdowns)."""
    qs = get_visible_categories(user=user)
    return list(
        qs.values("id", "name", "icon", "color", "is_system", "owner_id", "parent_id", "ordering")
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py -k "selector or visible or tree or flat" -v
```

Expected: All 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/categories/selectors.py backend/apps/categories/tests/test_services.py
git commit -m "feat(categories): add category selectors (visible, tree, flat)"
```

---

## Task 5: Category Services

**Files:**
- Create: `backend/apps/categories/services.py`
- Create: `backend/apps/categories/tests/factories.py`

- [ ] **Step 1: Write factories**

Create `backend/apps/categories/tests/factories.py`:

```python
from __future__ import annotations

import factory

from apps.categories.models import Category
from apps.users.tests.factories import UserFactory


class SystemCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"System Category {n}")
    is_system = True
    owner = None


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"User Category {n}")
    is_system = False
    owner = factory.SubFactory(UserFactory)
    parent = None
```

- [ ] **Step 2: Write failing service tests**

Add to `backend/apps/categories/tests/test_services.py`:

```python
from apps.categories.services import create_category, soft_delete_category, update_category
from apps.categories.tests.factories import CategoryFactory, SystemCategoryFactory
from common.exceptions import (
    CategoryCycleError,
    CategoryDepthError,
    CategoryPermissionError,
)


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
    with pytest.raises(CategoryCycleError):
        create_category(user=user, name="C", parent_id=b.id, icon="", color="", ordering=0)
    # Now set a's parent to b to create a cycle
    # Actually we test: trying to set b's parent back to a child of b
    c = CategoryFactory(owner=user, parent=b)
    with pytest.raises(CategoryCycleError):
        update_category(category=a, user=user, parent_id=c.id)


@pytest.mark.django_db
def test_create_category_max_depth_raises(db):
    user = UserFactory()
    # Build a chain of 10 categories
    parent = CategoryFactory(owner=user)
    for _ in range(9):
        parent = CategoryFactory(owner=user, parent=parent)
    # Now trying to add an 11th level should fail
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
```

- [ ] **Step 3: Run to verify they fail**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py -k "service or create or update or delete or cycle or depth" -v
```

Expected: `ImportError` — services module doesn't exist yet.

- [ ] **Step 4: Write `backend/apps/categories/services.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from common.exceptions import (
    CategoryCycleError,
    CategoryDepthError,
    CategoryPermissionError,
)

from .models import MAX_CATEGORY_DEPTH, Category

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


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
    """Return 1-based depth of the node that would have parent_id as its parent."""
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
    user: "AbstractBaseUser",
    name: str,
    parent_id: int | None,
    icon: str = "",
    color: str = "",
    ordering: int = 0,
) -> Category:
    if parent_id is not None:
        _check_no_cycle(category_id=None, new_parent_id=parent_id)
        depth = _measure_depth(parent_id)
        if depth >= MAX_CATEGORY_DEPTH:
            raise CategoryDepthError(f"Maximum category depth ({MAX_CATEGORY_DEPTH}) exceeded.")

    return Category.objects.create(
        name=name,
        parent_id=parent_id,
        owner=user,
        is_system=False,
        icon=icon,
        color=color,
        ordering=ordering,
    )


def update_category(
    *,
    category: Category,
    user: "AbstractBaseUser",
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


def soft_delete_category(*, category: Category, user: "AbstractBaseUser") -> None:
    if category.is_system:
        raise CategoryPermissionError("System categories cannot be deleted.")
    if category.owner_id != user.pk:
        raise CategoryPermissionError("You do not own this category.")
    category.soft_delete()
```

- [ ] **Step 5: Run service tests to verify they pass**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py -v
```

Expected: All tests `PASSED`.

- [ ] **Step 6: Run linter + type check**

```bash
docker compose exec backend ruff check apps/categories/
docker compose exec backend mypy apps/categories/
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/categories/services.py backend/apps/categories/tests/factories.py backend/apps/categories/tests/test_services.py
git commit -m "feat(categories): add category services with cycle/depth/permission guards"
```

---

## Task 6: Category Serializers + Views + URLs

**Files:**
- Create: `backend/apps/categories/serializers.py`
- Create: `backend/apps/categories/views.py`
- Create: `backend/apps/categories/urls.py`
- Modify: `backend/config/urls.py`

- [ ] **Step 1: Write failing view tests**

Create `backend/apps/categories/tests/test_views.py`:

```python
from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.categories.tests.factories import CategoryFactory, SystemCategoryFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def auth_client():
    user = UserFactory()
    client = APIClient()
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.user = user
    return client


@pytest.mark.django_db
def test_list_categories_tree_includes_system_and_own(auth_client):
    system = SystemCategoryFactory(name="Food")
    own = CategoryFactory(owner=auth_client.user, name="MyFood")
    other = CategoryFactory(name="OtherFood")  # different user

    resp = auth_client.get("/api/v1/categories/")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert system.id in ids
    assert own.id in ids
    assert other.id not in ids


@pytest.mark.django_db
def test_list_categories_flat_format(auth_client):
    SystemCategoryFactory(name="Food")
    CategoryFactory(owner=auth_client.user, name="MyFood")

    resp = auth_client.get("/api/v1/categories/?format=flat")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert "parent_id" in resp.json()[0]


@pytest.mark.django_db
def test_create_category(auth_client):
    resp = auth_client.post(
        "/api/v1/categories/",
        {"name": "Travel", "icon": "✈️", "color": "#2196F3", "ordering": 1},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Travel"
    assert data["is_system"] is False


@pytest.mark.django_db
def test_update_own_category(auth_client):
    cat = CategoryFactory(owner=auth_client.user, name="Old")
    resp = auth_client.patch(
        f"/api/v1/categories/{cat.id}/",
        {"name": "New"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


@pytest.mark.django_db
def test_update_system_category_forbidden(auth_client):
    system = SystemCategoryFactory()
    resp = auth_client.patch(
        f"/api/v1/categories/{system.id}/",
        {"name": "Hacked"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_delete_own_category(auth_client):
    cat = CategoryFactory(owner=auth_client.user)
    resp = auth_client.delete(f"/api/v1/categories/{cat.id}/")
    assert resp.status_code == 204
    cat.refresh_from_db()
    assert cat.deleted_at is not None


@pytest.mark.django_db
def test_delete_system_category_forbidden(auth_client):
    system = SystemCategoryFactory()
    resp = auth_client.delete(f"/api/v1/categories/{system.id}/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_request_rejected(db):
    client = APIClient()
    resp = client.get("/api/v1/categories/")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to verify tests fail**

```bash
docker compose exec backend pytest apps/categories/tests/test_views.py -v
```

Expected: `404` or `ImportError` — no URL registered yet.

- [ ] **Step 3: Write `backend/apps/categories/serializers.py`**

```python
from __future__ import annotations

from rest_framework import serializers

from .models import Category


class CategoryFlatSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", allow_null=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "icon",
            "color",
            "is_system",
            "owner_id",
            "parent_id",
            "ordering",
            "created_at",
        ]
        read_only_fields = ["id", "is_system", "owner_id", "created_at"]


class CategoryWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    parent_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    icon = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    color = serializers.CharField(max_length=7, allow_blank=True, required=False, default="")
    ordering = serializers.IntegerField(required=False, default=0)
```

- [ ] **Step 4: Write `backend/apps/categories/views.py`**

```python
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    CategoryCycleError,
    CategoryDepthError,
    CategoryNotFoundError,
    CategoryPermissionError,
)

from . import selectors, services
from .models import Category
from .serializers import CategoryFlatSerializer, CategoryWriteSerializer


def _get_visible_category_or_404(pk: int, user) -> Category:
    from django.db.models import Q

    try:
        return Category.objects.get(Q(is_system=True) | Q(owner=user), id=pk)
    except Category.DoesNotExist:
        raise CategoryNotFoundError(f"Category {pk} not found.")


class CategoryListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[OpenApiParameter("format", str, enum=["tree", "flat"], description="Response format")],
    )
    def get(self, request: Request) -> Response:
        fmt = request.query_params.get("format", "tree")
        qs = selectors.get_visible_categories(user=request.user)
        if fmt == "flat":
            return Response(selectors.get_category_flat(user=request.user))
        return Response(selectors.build_category_tree(qs))

    def post(self, request: Request) -> Response:
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = services.create_category(user=request.user, **serializer.validated_data)
        except (CategoryCycleError, CategoryDepthError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(CategoryFlatSerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request: Request, pk: int) -> Response:
        category = _get_visible_category_or_404(pk, request.user)
        serializer = CategoryWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            category = services.update_category(
                category=category, user=request.user, **serializer.validated_data
            )
        except CategoryPermissionError as exc:
            return Response(
                {"error": {"type": "CATEGORY_PERMISSION_DENIED", "detail": str(exc), "status": 403}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except (CategoryCycleError, CategoryDepthError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(CategoryFlatSerializer(category).data)

    def delete(self, request: Request, pk: int) -> Response:
        category = _get_visible_category_or_404(pk, request.user)
        try:
            services.soft_delete_category(category=category, user=request.user)
        except CategoryPermissionError as exc:
            return Response(
                {"error": {"type": "CATEGORY_PERMISSION_DENIED", "detail": str(exc), "status": 403}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Write `backend/apps/categories/urls.py`**

```python
from __future__ import annotations

from django.urls import URLPattern, path

from .views import CategoryDetailView, CategoryListView

urlpatterns: list[URLPattern] = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
]
```

- [ ] **Step 6: Register in `backend/config/urls.py`**

Add to `api_v1_patterns`:

```python
api_v1_patterns: list[URLPattern | URLResolver] = [
    path("", include("common.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.currencies.urls")),
    path("", include("apps.categories.urls")),   # ← add this
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
```

- [ ] **Step 7: Run view tests to verify they pass**

```bash
docker compose exec backend pytest apps/categories/tests/test_views.py -v
```

Expected: All tests `PASSED`.

- [ ] **Step 8: Run full test suite to check for regressions**

```bash
docker compose exec backend pytest --cov=. --cov-report=term-missing -q
```

Expected: All existing tests pass, no coverage drop below 90%.

- [ ] **Step 9: Commit**

```bash
git add backend/apps/categories/serializers.py backend/apps/categories/views.py backend/apps/categories/urls.py backend/apps/categories/tests/test_views.py backend/config/urls.py
git commit -m "feat(categories): add category serializers, views, and URL patterns"
```

---

## Task 7: System Categories Seed Migration

**Files:**
- Create: `backend/apps/categories/migrations/0002_seed_system_categories.py`

- [ ] **Step 1: Write failing test for seed data**

Add to `backend/apps/categories/tests/test_services.py`:

```python
@pytest.mark.django_db
def test_system_categories_seeded(db):
    """After migrations, at least 6 system categories exist."""
    count = Category.objects.filter(is_system=True).count()
    assert count >= 6
```

- [ ] **Step 2: Run to verify it fails**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py::test_system_categories_seeded -v
```

Expected: `FAILED` — 0 system categories exist.

- [ ] **Step 3: Write `backend/apps/categories/migrations/0002_seed_system_categories.py`**

```python
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
```

- [ ] **Step 4: Run migration**

```bash
docker compose exec backend python manage.py migrate
```

Expected: `Applying categories.0002_seed_system_categories... OK`

- [ ] **Step 5: Run test to verify it passes**

```bash
docker compose exec backend pytest apps/categories/tests/test_services.py::test_system_categories_seeded -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add backend/apps/categories/migrations/0002_seed_system_categories.py backend/apps/categories/tests/test_services.py
git commit -m "feat(categories): seed 7 system categories via data migration"
```

---

## Task 8: Transaction Model + Migration

**Files:**
- Create: `backend/apps/transactions/models.py`
- Modify: `backend/apps/currencies/services.py` (add `get_exchange_rate`)

- [ ] **Step 1: Add `get_exchange_rate()` to currencies services**

In `backend/apps/currencies/services.py`, add after the `convert()` function:

```python
def get_exchange_rate(from_code: str, to_code: str, *, at: date_type) -> Decimal:
    """Return the raw exchange rate for a currency pair at the given date.

    Same direct/inverse/fallback logic as _lookup_rate. Used when callers need
    the rate itself (e.g. to store as fx_rate_snapshot), not the converted amount.
    """
    if from_code == to_code:
        return Decimal("1")
    rate = _lookup_rate(from_code, to_code, at)
    if rate is None:
        raise RateNotFoundError(f"No FX rate for {from_code}->{to_code} on or before {at}")
    return rate
```

- [ ] **Step 2: Write failing model test**

Create `backend/apps/transactions/tests/test_services.py`:

```python
from __future__ import annotations

import pytest

from apps.transactions.models import Transaction


@pytest.mark.django_db
def test_transaction_model_exists():
    fields = {f.name for f in Transaction._meta.get_fields()}
    assert "amount" in fields
    assert "amount_base" in fields
    assert "fx_rate_snapshot" in fields
    assert "currency_code" in fields
    assert "type" in fields
    assert "category" in fields
    assert "deleted_at" in fields
```

- [ ] **Step 3: Run to verify it fails**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py::test_transaction_model_exists -v
```

Expected: `ImportError` — model doesn't exist yet.

- [ ] **Step 4: Write `backend/apps/transactions/models.py`**

```python
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models

from apps.categories.models import Category
from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()

INCOME = "income"
EXPENSE = "expense"
TRANSACTION_TYPE_CHOICES = [
    (INCOME, "Income"),
    (EXPENSE, "Expense"),
]


class Transaction(TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency_code = models.CharField(max_length=10)
    amount_base = models.DecimalField(max_digits=20, decimal_places=8)
    base_currency = models.CharField(max_length=10)
    fx_rate_snapshot = models.DecimalField(max_digits=20, decimal_places=8)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "type"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} {self.amount} {self.currency_code} on {self.date}"
```

- [ ] **Step 5: Generate and run migration**

```bash
docker compose exec backend python manage.py makemigrations transactions --name initial
docker compose exec backend python manage.py migrate
```

Expected: `Applying transactions.0001_initial... OK`

- [ ] **Step 6: Run test to verify it passes**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py::test_transaction_model_exists -v
```

Expected: `PASSED`

- [ ] **Step 7: Register in admin**

Update `backend/apps/transactions/admin.py`:

```python
from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "amount", "currency_code", "date", "category"]
    list_filter = ["type", "currency_code"]
    search_fields = ["description", "reference"]
    date_hierarchy = "date"
```

- [ ] **Step 8: Commit**

```bash
git add backend/apps/transactions/ backend/apps/currencies/services.py
git commit -m "feat(transactions): add Transaction model, migration, and get_exchange_rate helper"
```

---

## Task 9: Transaction Services

**Files:**
- Create: `backend/apps/transactions/services.py`
- Create: `backend/apps/transactions/tests/factories.py`

- [ ] **Step 1: Write factories**

Create `backend/apps/transactions/tests/factories.py`:

```python
from __future__ import annotations

import factory
from decimal import Decimal
from datetime import date as date_type

from apps.transactions.models import EXPENSE, Transaction
from apps.users.tests.factories import UserFactory


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SubFactory(UserFactory)
    type = EXPENSE
    amount = Decimal("100.00000000")
    currency_code = "USD"
    amount_base = Decimal("100.00000000")
    base_currency = "USD"
    fx_rate_snapshot = Decimal("1.00000000")
    category = None
    date = factory.LazyFunction(date_type.today)
    description = ""
    reference = ""
```

- [ ] **Step 2: Write failing service tests**

Add to `backend/apps/transactions/tests/test_services.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.categories.tests.factories import CategoryFactory, SystemCategoryFactory
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory
from apps.transactions.models import Transaction
from apps.transactions.services import create_transaction, soft_delete_transaction, update_transaction
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory
from common.exceptions import TransactionNotFoundError


@pytest.mark.django_db
def test_create_transaction_same_currency(db):
    """When currency equals user default, fx_rate_snapshot=1 and amount_base=amount."""
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")

    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("50.00"),
        currency_code="USD",
        category_id=None,
        date=date.today(),
        description="Test",
        reference="",
    )

    assert tx.amount == Decimal("50.00")
    assert tx.fx_rate_snapshot == Decimal("1")
    assert tx.amount_base == Decimal("50.00")
    assert tx.base_currency == "USD"


@pytest.mark.django_db
def test_create_transaction_foreign_currency_snapshots_rate(db):
    """FX snapshot is stored; amount_base is amount * rate."""
    user = UserFactory()
    user.default_currency_code = "TRY"
    user.save()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33.00000000"), rate_date=date.today())

    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("10.00000000"),
        currency_code="USD",
        category_id=None,
        date=date.today(),
        description="",
        reference="",
    )

    assert tx.fx_rate_snapshot == Decimal("33.00000000")
    assert tx.amount_base == Decimal("330.00000000")


@pytest.mark.django_db
def test_create_transaction_with_category(db):
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    system_cat = SystemCategoryFactory()

    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("20.00"),
        currency_code="USD",
        category_id=system_cat.id,
        date=date.today(),
        description="",
        reference="",
    )
    assert tx.category_id == system_cat.id


@pytest.mark.django_db
def test_update_transaction_amount_recalculates_fx(db):
    """Updating amount triggers FX recalculation."""
    user = UserFactory()
    user.default_currency_code = "TRY"
    user.save()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33.00000000"), rate_date=date.today())

    tx = TransactionFactory(
        user=user,
        currency_code="USD",
        base_currency="TRY",
        amount=Decimal("10.00000000"),
        amount_base=Decimal("330.00000000"),
        fx_rate_snapshot=Decimal("33.00000000"),
    )

    updated = update_transaction(transaction=tx, user=user, amount=Decimal("20.00000000"))
    assert updated.amount_base == Decimal("660.00000000")
    assert updated.fx_rate_snapshot == Decimal("33.00000000")


@pytest.mark.django_db
def test_update_transaction_description_preserves_fx(db):
    """Updating non-monetary fields preserves the FX snapshot."""
    user = UserFactory()
    tx = TransactionFactory(
        user=user,
        fx_rate_snapshot=Decimal("33.00000000"),
        amount_base=Decimal("330.00000000"),
    )

    updated = update_transaction(transaction=tx, user=user, description="New description")
    assert updated.fx_rate_snapshot == Decimal("33.00000000")
    assert updated.amount_base == Decimal("330.00000000")
    assert updated.description == "New description"


@pytest.mark.django_db
def test_soft_delete_transaction(db):
    user = UserFactory()
    tx = TransactionFactory(user=user)
    soft_delete_transaction(transaction=tx, user=user)
    tx.refresh_from_db()
    assert tx.deleted_at is not None
    assert Transaction.objects.filter(id=tx.id).count() == 0
    assert Transaction.all_objects.filter(id=tx.id).count() == 1


@pytest.mark.django_db
def test_soft_delete_other_user_transaction_raises(db):
    user = UserFactory()
    other = UserFactory()
    tx = TransactionFactory(user=other)
    with pytest.raises(TransactionNotFoundError):
        soft_delete_transaction(transaction=tx, user=user)
```

- [ ] **Step 3: Run to verify they fail**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py -v
```

Expected: `ImportError` — services module doesn't exist yet.

- [ ] **Step 4: Write `backend/apps/transactions/services.py`**

```python
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import Q

from apps.categories.models import Category
from apps.currencies.models import Currency
from apps.currencies.services import RateNotFoundError, get_exchange_rate
from common.exceptions import CategoryNotFoundError, CategoryPermissionError, TransactionNotFoundError
from common.exceptions import UnknownCurrencyError  # noqa: F401 (re-export for views)

from .models import Transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

QUANTIZE = Decimal("0.00000001")


def _get_accessible_category(*, category_id: int, user: "AbstractBaseUser") -> Category:
    try:
        return Category.objects.get(Q(is_system=True) | Q(owner=user), id=category_id)
    except Category.DoesNotExist:
        raise CategoryNotFoundError(f"Category {category_id} not found or not accessible.")


def _compute_fx(
    *,
    amount: Decimal,
    currency_code: str,
    base_currency: str,
    tx_date: date_type,
) -> tuple[Decimal, Decimal]:
    """Return (amount_base, fx_rate_snapshot). Short-circuits when currencies match."""
    if currency_code == base_currency:
        return amount, Decimal("1")
    rate = get_exchange_rate(currency_code, base_currency, at=tx_date)
    return (amount * rate).quantize(QUANTIZE), rate


def create_transaction(
    *,
    user: "AbstractBaseUser",
    type: str,
    amount: Decimal,
    currency_code: str,
    category_id: int | None,
    date: date_type,
    description: str = "",
    reference: str = "",
) -> Transaction:
    if not Currency.objects.filter(code=currency_code).exists():
        raise UnknownCurrencyError(f"Unknown currency: {currency_code}")

    category = None
    if category_id is not None:
        category = _get_accessible_category(category_id=category_id, user=user)

    base_currency: str = user.default_currency_code  # type: ignore[attr-defined]
    amount_base, fx_rate_snapshot = _compute_fx(
        amount=amount,
        currency_code=currency_code,
        base_currency=base_currency,
        tx_date=date,
    )

    return Transaction.objects.create(
        user=user,
        type=type,
        amount=amount,
        currency_code=currency_code,
        amount_base=amount_base,
        base_currency=base_currency,
        fx_rate_snapshot=fx_rate_snapshot,
        category=category,
        date=date,
        description=description,
        reference=reference,
    )


def update_transaction(
    *,
    transaction: Transaction,
    user: "AbstractBaseUser",
    **fields: Any,
) -> Transaction:
    if transaction.user_id != user.pk:
        raise TransactionNotFoundError("Transaction not found.")

    fx_fields_changed = "amount" in fields or "currency_code" in fields

    if "category_id" in fields and fields["category_id"] is not None:
        _get_accessible_category(category_id=fields["category_id"], user=user)

    for attr, value in fields.items():
        setattr(transaction, attr, value)

    if fx_fields_changed:
        base_currency: str = user.default_currency_code  # type: ignore[attr-defined]
        transaction.base_currency = base_currency
        transaction.amount_base, transaction.fx_rate_snapshot = _compute_fx(
            amount=transaction.amount,
            currency_code=transaction.currency_code,
            base_currency=base_currency,
            tx_date=transaction.date,
        )

    transaction.save()
    return transaction


def soft_delete_transaction(*, transaction: Transaction, user: "AbstractBaseUser") -> None:
    if transaction.user_id != user.pk:
        raise TransactionNotFoundError("Transaction not found.")
    transaction.soft_delete()
```

- [ ] **Step 5: Run service tests to verify they pass**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py -v
```

Expected: All tests `PASSED`.

- [ ] **Step 6: Run linter + type check**

```bash
docker compose exec backend ruff check apps/transactions/
docker compose exec backend mypy apps/transactions/
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/transactions/services.py backend/apps/transactions/tests/factories.py backend/apps/transactions/tests/test_services.py
git commit -m "feat(transactions): add transaction services with FX snapshot logic"
```

---

## Task 10: Transaction Selectors

**Files:**
- Create: `backend/apps/transactions/selectors.py`

- [ ] **Step 1: Write failing selector tests**

Add to `backend/apps/transactions/tests/test_services.py`:

```python
from apps.transactions.selectors import get_transaction_list, get_transaction_summary


@pytest.mark.django_db
def test_get_transaction_list_filters_by_type(db):
    user = UserFactory()
    CurrencyFactory(code="USD")
    expense = TransactionFactory(user=user, type="expense")
    income = TransactionFactory(user=user, type="income")

    qs = get_transaction_list(user=user, filters={"type": "expense"})
    ids = list(qs.values_list("id", flat=True))
    assert expense.id in ids
    assert income.id not in ids


@pytest.mark.django_db
def test_get_transaction_list_search_description(db):
    user = UserFactory()
    CurrencyFactory(code="USD")
    tx1 = TransactionFactory(user=user, description="weekly groceries")
    tx2 = TransactionFactory(user=user, description="netflix subscription")

    qs = get_transaction_list(user=user, filters={"search": "groceries"})
    ids = list(qs.values_list("id", flat=True))
    assert tx1.id in ids
    assert tx2.id not in ids


@pytest.mark.django_db
def test_get_transaction_list_excludes_other_users(db):
    user = UserFactory()
    other = UserFactory()
    CurrencyFactory(code="USD")
    own_tx = TransactionFactory(user=user)
    other_tx = TransactionFactory(user=other)

    qs = get_transaction_list(user=user, filters={})
    ids = list(qs.values_list("id", flat=True))
    assert own_tx.id in ids
    assert other_tx.id not in ids


@pytest.mark.django_db
def test_get_transaction_summary_totals(db):
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")

    today = date.today()
    TransactionFactory(user=user, type="income", amount_base=Decimal("500.00"), base_currency="USD", date=today)
    TransactionFactory(user=user, type="expense", amount_base=Decimal("200.00"), base_currency="USD", date=today)

    summary = get_transaction_summary(
        user=user,
        date_from=today,
        date_to=today,
        group_by="day",
    )

    assert Decimal(summary["total_income"]) == Decimal("500.00000000")
    assert Decimal(summary["total_expense"]) == Decimal("200.00000000")
    assert Decimal(summary["net"]) == Decimal("300.00000000")
```

- [ ] **Step 2: Run to verify they fail**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py -k "selector or list or summary" -v
```

Expected: `ImportError` — selectors module doesn't exist yet.

- [ ] **Step 3: Write `backend/apps/transactions/selectors.py`**

```python
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import Case, Count, DecimalField, F, Q, QuerySet, Sum, When
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek

from .models import Transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

QUANTIZE = Decimal("0.00000001")

_ALLOWED_ORDERINGS = {"date", "-date", "amount", "-amount"}
_TRUNC_MAP = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}


def get_transaction_list(
    *,
    user: "AbstractBaseUser",
    filters: dict[str, Any],
) -> "QuerySet[Transaction]":
    qs = Transaction.objects.filter(user=user).select_related("category")

    if type_ := filters.get("type"):
        qs = qs.filter(type=type_)
    if category_id := filters.get("category"):
        qs = qs.filter(category_id=category_id)
    if currency := filters.get("currency"):
        qs = qs.filter(currency_code=currency)
    if date_from := filters.get("date_from"):
        qs = qs.filter(date__gte=date_from)
    if date_to := filters.get("date_to"):
        qs = qs.filter(date__lte=date_to)
    if amount_min := filters.get("amount_min"):
        qs = qs.filter(amount__gte=amount_min)
    if amount_max := filters.get("amount_max"):
        qs = qs.filter(amount__lte=amount_max)
    if search := filters.get("search"):
        qs = qs.filter(description__icontains=search)

    ordering = filters.get("ordering", "-date")
    if ordering not in _ALLOWED_ORDERINGS:
        ordering = "-date"
    return qs.order_by(ordering)


def get_transaction_summary(
    *,
    user: "AbstractBaseUser",
    date_from: date_type,
    date_to: date_type,
    group_by: str = "day",
) -> dict[str, Any]:
    qs = Transaction.objects.filter(user=user, date__range=(date_from, date_to))

    totals = qs.aggregate(
        total_income=Sum(
            Case(
                When(type="income", then=F("amount_base")),
                default=Decimal("0"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            )
        ),
        total_expense=Sum(
            Case(
                When(type="expense", then=F("amount_base")),
                default=Decimal("0"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            )
        ),
    )
    total_income = (totals["total_income"] or Decimal("0")).quantize(QUANTIZE)
    total_expense = (totals["total_expense"] or Decimal("0")).quantize(QUANTIZE)

    by_category = list(
        qs.values("category_id", "category__name")
        .annotate(total=Sum("amount_base"), count=Count("id"))
        .order_by("-total")
    )

    trunc_fn = _TRUNC_MAP.get(group_by, TruncDay)
    period_rows = (
        qs.annotate(
            signed=Case(
                When(type="income", then=F("amount_base")),
                default=-F("amount_base"),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            ),
            period=trunc_fn("date"),
        )
        .values("period")
        .annotate(period_net=Sum("signed"))
        .order_by("period")
    )

    cumulative = Decimal("0")
    running_balance = []
    for row in period_rows:
        cumulative += (row["period_net"] or Decimal("0"))
        running_balance.append(
            {
                "period": row["period"].isoformat() if row["period"] else None,
                "cumulative_net": str(cumulative.quantize(QUANTIZE)),
            }
        )

    return {
        "total_income": str(total_income),
        "total_expense": str(total_expense),
        "net": str((total_income - total_expense).quantize(QUANTIZE)),
        "by_category": by_category,
        "running_balance": running_balance,
    }
```

- [ ] **Step 4: Run selector tests to verify they pass**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py -v
```

Expected: All tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/transactions/selectors.py backend/apps/transactions/tests/test_services.py
git commit -m "feat(transactions): add transaction selectors with filters and summary aggregates"
```

---

## Task 11: Transaction Serializers + Views + URLs

**Files:**
- Create: `backend/apps/transactions/serializers.py`
- Create: `backend/apps/transactions/views.py`
- Create: `backend/apps/transactions/urls.py`
- Modify: `backend/config/urls.py`

- [ ] **Step 1: Write failing view tests**

Create `backend/apps/transactions/tests/test_views.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.categories.tests.factories import SystemCategoryFactory
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory
from apps.transactions.models import Transaction
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user():
    u = UserFactory()
    u.default_currency_code = "USD"
    u.save()
    return u


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.user = user
    return client


@pytest.fixture(autouse=True)
def usd_currency(db):
    return CurrencyFactory(code="USD")


@pytest.mark.django_db
def test_create_transaction(auth_client):
    resp = auth_client.post(
        "/api/v1/transactions/",
        {"type": "expense", "amount": "50.00", "currency_code": "USD", "date": str(date.today()), "description": "Test"},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "expense"
    assert Decimal(data["fx_rate_snapshot"]) == Decimal("1")
    assert data["base_currency"] == "USD"


@pytest.mark.django_db
def test_list_transactions(auth_client):
    TransactionFactory(user=auth_client.user)
    TransactionFactory(user=auth_client.user)
    other = UserFactory()
    TransactionFactory(user=other)

    resp = auth_client.get("/api/v1/transactions/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


@pytest.mark.django_db
def test_filter_by_type(auth_client):
    TransactionFactory(user=auth_client.user, type="expense")
    TransactionFactory(user=auth_client.user, type="income")

    resp = auth_client.get("/api/v1/transactions/?type=expense")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["type"] == "expense"


@pytest.mark.django_db
def test_filter_by_search(auth_client):
    TransactionFactory(user=auth_client.user, description="weekly groceries")
    TransactionFactory(user=auth_client.user, description="netflix")

    resp = auth_client.get("/api/v1/transactions/?search=groceries")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


@pytest.mark.django_db
def test_filter_by_amount_range(auth_client):
    TransactionFactory(user=auth_client.user, amount=Decimal("50.00"), amount_base=Decimal("50.00"))
    TransactionFactory(user=auth_client.user, amount=Decimal("200.00"), amount_base=Decimal("200.00"))

    resp = auth_client.get("/api/v1/transactions/?amount_min=100")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert Decimal(resp.json()["results"][0]["amount"]) == Decimal("200.00")


@pytest.mark.django_db
def test_get_transaction_detail(auth_client):
    tx = TransactionFactory(user=auth_client.user)
    resp = auth_client.get(f"/api/v1/transactions/{tx.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == tx.id


@pytest.mark.django_db
def test_get_other_user_transaction_returns_404(auth_client):
    other = UserFactory()
    tx = TransactionFactory(user=other)
    resp = auth_client.get(f"/api/v1/transactions/{tx.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_update_transaction(auth_client):
    tx = TransactionFactory(user=auth_client.user, description="old")
    resp = auth_client.patch(
        f"/api/v1/transactions/{tx.id}/",
        {"description": "new"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "new"


@pytest.mark.django_db
def test_delete_transaction(auth_client):
    tx = TransactionFactory(user=auth_client.user)
    resp = auth_client.delete(f"/api/v1/transactions/{tx.id}/")
    assert resp.status_code == 204
    assert Transaction.objects.filter(id=tx.id).count() == 0


@pytest.mark.django_db
def test_summary_endpoint(auth_client):
    today = date.today()
    TransactionFactory(user=auth_client.user, type="income", amount_base=Decimal("1000.00"), date=today)
    TransactionFactory(user=auth_client.user, type="expense", amount_base=Decimal("400.00"), date=today)

    resp = auth_client.get(f"/api/v1/transactions/summary/?date_from={today}&date_to={today}&group_by=month")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_income"]) == Decimal("1000.00000000")
    assert Decimal(data["total_expense"]) == Decimal("400.00000000")
    assert Decimal(data["net"]) == Decimal("600.00000000")
    assert len(data["running_balance"]) == 1


@pytest.mark.django_db
def test_unauthenticated_rejected(db):
    client = APIClient()
    resp = client.get("/api/v1/transactions/")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to verify tests fail**

```bash
docker compose exec backend pytest apps/transactions/tests/test_views.py -v
```

Expected: `404` or `ImportError` — no URL registered yet.

- [ ] **Step 3: Write `backend/apps/transactions/serializers.py`**

```python
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from rest_framework import serializers

from apps.transactions.models import EXPENSE, INCOME, Transaction


class CategorySummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    color = serializers.CharField()
    icon = serializers.CharField()
    parent_name = serializers.SerializerMethodField()

    def get_parent_name(self, obj) -> str | None:
        return obj.parent.name if obj.parent_id else None


class TransactionSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "type",
            "amount",
            "currency_code",
            "amount_base",
            "base_currency",
            "fx_rate_snapshot",
            "category",
            "date",
            "description",
            "reference",
            "created_at",
        ]

    def get_category(self, obj: Transaction) -> dict | None:
        if obj.category is None:
            return None
        cat = obj.category
        return {
            "id": cat.id,
            "name": cat.name,
            "color": cat.color,
            "icon": cat.icon,
            "parent_name": cat.parent.name if cat.parent_id else None,
        }


class TransactionWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[INCOME, EXPENSE])
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, min_value=Decimal("0.00000001"))
    currency_code = serializers.CharField(max_length=10)
    category_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    date = serializers.DateField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    reference = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")


class TransactionFilterSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[INCOME, EXPENSE], required=False)
    category = serializers.IntegerField(required=False)
    currency = serializers.CharField(max_length=10, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    amount_min = serializers.DecimalField(max_digits=20, decimal_places=8, required=False)
    amount_max = serializers.DecimalField(max_digits=20, decimal_places=8, required=False)
    search = serializers.CharField(max_length=200, required=False)
    ordering = serializers.CharField(max_length=20, required=False)


class TransactionSummaryQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    group_by = serializers.ChoiceField(choices=["day", "week", "month"], required=False, default="day")
```

- [ ] **Step 4: Write `backend/apps/transactions/views.py`**

```python
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    CategoryNotFoundError,
    CategoryPermissionError,
    TransactionNotFoundError,
)

from . import selectors, services
from .models import Transaction
from .serializers import (
    TransactionFilterSerializer,
    TransactionSerializer,
    TransactionSummaryQuerySerializer,
    TransactionWriteSerializer,
)


class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _get_own_transaction_or_404(pk: int, user) -> Transaction:
    try:
        return Transaction.objects.get(id=pk, user=user)
    except Transaction.DoesNotExist:
        raise TransactionNotFoundError(f"Transaction {pk} not found.")


class TransactionListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        filter_serializer = TransactionFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        qs = selectors.get_transaction_list(user=request.user, filters=filter_serializer.validated_data)

        paginator = TransactionPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = TransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = TransactionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tx = services.create_transaction(user=request.user, **serializer.validated_data)
        except (CategoryNotFoundError, CategoryPermissionError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class TransactionDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, pk: int) -> Response:
        tx = _get_own_transaction_or_404(pk, request.user)
        return Response(TransactionSerializer(tx).data)

    def patch(self, request: Request, pk: int) -> Response:
        tx = _get_own_transaction_or_404(pk, request.user)
        serializer = TransactionWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            tx = services.update_transaction(transaction=tx, user=request.user, **serializer.validated_data)
        except (CategoryNotFoundError, CategoryPermissionError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(TransactionSerializer(tx).data)

    def delete(self, request: Request, pk: int) -> Response:
        tx = _get_own_transaction_or_404(pk, request.user)
        services.soft_delete_transaction(transaction=tx, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = selectors.get_transaction_summary(user=request.user, **query_serializer.validated_data)
        return Response(data)
```

- [ ] **Step 5: Write `backend/apps/transactions/urls.py`**

```python
from __future__ import annotations

from django.urls import URLPattern, path

from .views import TransactionDetailView, TransactionListView, TransactionSummaryView

urlpatterns: list[URLPattern] = [
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path("transactions/summary/", TransactionSummaryView.as_view(), name="transaction-summary"),
    path("transactions/<int:pk>/", TransactionDetailView.as_view(), name="transaction-detail"),
]
```

- [ ] **Step 6: Register in `backend/config/urls.py`**

```python
api_v1_patterns: list[URLPattern | URLResolver] = [
    path("", include("common.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.currencies.urls")),
    path("", include("apps.categories.urls")),
    path("", include("apps.transactions.urls")),   # ← add this
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
```

- [ ] **Step 7: Run view tests**

```bash
docker compose exec backend pytest apps/transactions/tests/test_views.py -v
```

Expected: All tests `PASSED`.

- [ ] **Step 8: Run full test suite + coverage check**

```bash
docker compose exec backend pytest --cov=. --cov-report=term-missing -q
```

Expected: ≥90% coverage, all tests pass.

- [ ] **Step 9: Run lint + type check**

```bash
docker compose exec backend ruff check .
docker compose exec backend mypy .
```

Expected: No errors.

- [ ] **Step 10: Commit**

```bash
git add backend/apps/transactions/serializers.py backend/apps/transactions/views.py backend/apps/transactions/urls.py backend/apps/transactions/tests/test_views.py backend/config/urls.py
git commit -m "feat(transactions): add transaction serializers, views, and URL patterns"
```

---

## Task 12: E2E Test + CLAUDE.md Update

**Files:**
- Create: `backend/apps/transactions/tests/test_e2e.py`
- Modify: `backend/CLAUDE.md`

- [ ] **Step 1: Write E2E flow test**

Create `backend/apps/transactions/tests/test_e2e.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.currencies.tests.factories import CurrencyFactory, FxRateFactory
from apps.transactions.models import Transaction
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_full_transaction_flow(db):
    """
    Full Phase 4 flow:
    register → login → create subcategory under system category
    → create expense (USD) → verify FX snapshot
    → create income (TRY) → verify rate=1
    → filter by category → search by description
    → get monthly summary → verify running balance
    → soft delete → verify not in list
    """
    # Setup
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    today = date.today()
    FxRateFactory(base_code="USD", quote_code="TRY", rate=Decimal("33.00000000"), rate_date=today)

    # System category exists from seed migration
    food = Category.objects.create(name="Food", is_system=True)

    # Register user
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/register/",
        {"email": "e2e@ledgr.io", "password": "SuperSecure123!", "default_currency_code": "TRY"},
        format="json",
    )
    assert resp.status_code == 201

    # Login
    resp = client.post(
        "/api/v1/auth/login/",
        {"email": "e2e@ledgr.io", "password": "SuperSecure123!"},
        format="json",
    )
    assert resp.status_code == 200
    access = resp.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # Create user subcategory under system category
    resp = client.post(
        "/api/v1/categories/",
        {"name": "Restaurant", "parent_id": food.id, "icon": "🍽️", "color": "#FF9800"},
        format="json",
    )
    assert resp.status_code == 201
    restaurant_id = resp.json()["id"]

    # Create expense in USD (user default is TRY → FX snapshot expected)
    resp = client.post(
        "/api/v1/transactions/",
        {
            "type": "expense",
            "amount": "10.00000000",
            "currency_code": "USD",
            "category_id": restaurant_id,
            "date": str(today),
            "description": "lunch at restaurant",
        },
        format="json",
    )
    assert resp.status_code == 201
    expense = resp.json()
    assert Decimal(expense["fx_rate_snapshot"]) == Decimal("33.00000000")
    assert Decimal(expense["amount_base"]) == Decimal("330.00000000")
    assert expense["base_currency"] == "TRY"
    expense_id = expense["id"]

    # Create income in TRY (same as default → rate=1)
    resp = client.post(
        "/api/v1/transactions/",
        {
            "type": "income",
            "amount": "5000.00000000",
            "currency_code": "TRY",
            "date": str(today),
            "description": "salary",
        },
        format="json",
    )
    assert resp.status_code == 201
    income = resp.json()
    assert Decimal(income["fx_rate_snapshot"]) == Decimal("1")
    assert Decimal(income["amount_base"]) == Decimal("5000.00000000")

    # Filter by category
    resp = client.get(f"/api/v1/transactions/?category={restaurant_id}")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    # Search by description
    resp = client.get("/api/v1/transactions/?search=lunch")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    # Monthly summary
    resp = client.get(f"/api/v1/transactions/summary/?date_from={today}&date_to={today}&group_by=month")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_income"]) == Decimal("5000.00000000")
    assert Decimal(data["total_expense"]) == Decimal("330.00000000")
    assert Decimal(data["net"]) == Decimal("4670.00000000")
    assert len(data["running_balance"]) == 1

    # Soft delete expense
    resp = client.delete(f"/api/v1/transactions/{expense_id}/")
    assert resp.status_code == 204

    # Verify not in list
    resp = client.get("/api/v1/transactions/")
    assert resp.status_code == 200
    ids = [tx["id"] for tx in resp.json()["results"]]
    assert expense_id not in ids

    # Verify still in DB via all_objects
    assert Transaction.all_objects.filter(id=expense_id).exists()
```

- [ ] **Step 2: Run E2E test**

```bash
docker compose exec backend pytest apps/transactions/tests/test_e2e.py -v
```

Expected: `PASSED`

- [ ] **Step 3: Run full coverage check**

```bash
docker compose exec backend pytest --cov=. --cov-report=term-missing -q
```

Expected: ≥94% coverage, all tests pass.

- [ ] **Step 4: Update CLAUDE.md Phase 4 row**

In `backend/CLAUDE.md` (or root `CLAUDE.md`), update the Faz Planı table:

Find:
```
| 4. Transactions + Categories | ⏳ Pending | Multi-currency snapshot, hiyerarşik kategori, window function summary |
```

Replace with:
```
| **4. Transactions + Categories** | ✅ **Tamamlandı** | `apps/categories/` (7 system cats, unlimited hierarchy, system/user-owned, soft delete) + `apps/transactions/` (income/expense, FX snapshot at write time, filters: type/category/currency/date/amount/search, summary: totals + running balance by day/week/month). ~40 yeni test. |
```

- [ ] **Step 5: Final lint + type check**

```bash
docker compose exec backend ruff check .
docker compose exec backend mypy .
```

Expected: No errors.

- [ ] **Step 6: Final commit**

```bash
git add backend/apps/transactions/tests/test_e2e.py CLAUDE.md
git commit -m "test(phase4): add E2E transaction flow test and update CLAUDE.md"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All spec sections have corresponding tasks — category CRUD, unlimited hierarchy with cycle/depth guards, system/user-owned distinction, transaction FX snapshot, dual amount fields, all filter params, summary with running balance, nested category in transaction response, format=tree/flat, group_by param.
- [x] **Placeholder scan:** No TBDs, TODOs, or "implement later" phrases. All code blocks are complete.
- [x] **Type consistency:** `create_category` / `update_category` / `soft_delete_category` signatures match their test calls. `create_transaction` / `update_transaction` / `soft_delete_transaction` signatures match their test calls and view usage. `get_transaction_list` takes `filters: dict`, `get_transaction_summary` takes `date_from, date_to, group_by` — matches `TransactionSummaryQuerySerializer` fields and view call.
- [x] **Dependency order:** categories app fully implemented before transactions references it.
- [x] **`get_exchange_rate()`** added to `currencies/services.py` in Task 8 before `transactions/services.py` calls it in the same task.
