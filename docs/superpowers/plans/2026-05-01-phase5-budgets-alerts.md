# Phase 5 — Budgets + Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `budgets` app: category-scoped spending budgets with Subquery-based live usage and an idempotent Celery beat email alert at 07:00 UTC.

**Architecture:** `Budget` model stores user-scoped spending limits with optional category and threshold. `spent` is computed live via a `Subquery` over `Transaction.amount_base` (no derived storage). Alert service is idempotent via `alert_sent_at` guard; beat task registered via data migration following D-003 pattern.

**Tech Stack:** Django 5 / DRF · `decimal.Decimal` · `django.db.models.Subquery + Case/When` · `django.core.mail.send_mail` · Celery beat (DatabaseScheduler) · `factory_boy` · `pytest-django`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/apps/transactions/services.py` | Add `fx_rate_override` param (D-012) |
| Modify | `backend/apps/transactions/tests/test_services.py` | Tests for `fx_rate_override` |
| Modify | `backend/common/exceptions.py` | Add `BudgetNotFoundError`, `BudgetInvalidError` |
| Modify | `backend/config/settings/base.py` | Add `apps.budgets` to `LOCAL_APPS` |
| Modify | `backend/config/urls.py` | Add `budgets/` URL |
| Create | `backend/apps/budgets/__init__.py` | App package marker |
| Create | `backend/apps/budgets/apps.py` | AppConfig |
| Create | `backend/apps/budgets/models.py` | `Budget` model + DB constraints |
| Create | `backend/apps/budgets/migrations/__init__.py` | Migrations package |
| Create | `backend/apps/budgets/migrations/0001_initial.py` | Auto-generated |
| Create | `backend/apps/budgets/migrations/0002_register_budget_alert_beat.py` | Beat task registration |
| Create | `backend/apps/budgets/selectors.py` | `get_budget_queryset`, `get_budget_for_user`, `get_all_active_budgets_for_alert` |
| Create | `backend/apps/budgets/services.py` | `create_budget`, `update_budget`, `delete_budget`, `check_and_send_budget_alerts` |
| Create | `backend/apps/budgets/serializers.py` | Input/output serializers |
| Create | `backend/apps/budgets/views.py` | `BudgetListCreateView`, `BudgetDetailView` |
| Create | `backend/apps/budgets/urls.py` | URL patterns |
| Create | `backend/apps/budgets/tasks.py` | `send_budget_alerts` Celery task |
| Create | `backend/apps/budgets/tests/__init__.py` | Test package |
| Create | `backend/apps/budgets/tests/factories.py` | `BudgetFactory` |
| Create | `backend/apps/budgets/tests/test_services.py` | Service + selector unit tests |
| Create | `backend/apps/budgets/tests/test_views.py` | API integration tests |

---

## Task 1: D-012 — fx_rate_override in transaction services

**Files:**
- Modify: `backend/apps/transactions/services.py`
- Modify: `backend/apps/transactions/tests/test_services.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/transactions/tests/test_services.py`:

```python
@pytest.mark.django_db
def test_create_transaction_fx_rate_override_skips_convert(db):
    """When fx_rate_override is given, get_exchange_rate is not called."""
    user = UserFactory()
    user.default_currency_code = "TRY"
    user.save()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    account = AccountFactory(user=user, currency_code="USD")

    # No FxRate seeded — would fail with StaleFxRateError without override
    tx = create_transaction(
        user=user,
        account=account,
        type="expense",
        amount=Decimal("10.00000000"),
        currency_code="USD",
        category_id=None,
        date=date(2020, 1, 15),
        description="Old rent",
        reference="",
        fx_rate_override=Decimal("7.50000000"),
    )

    assert tx.fx_rate_snapshot == Decimal("7.50000000")
    assert tx.amount_base == Decimal("75.00000000")


@pytest.mark.django_db
def test_create_transaction_fx_rate_override_same_currency_ignored(db):
    """When currency == base, override is irrelevant — snapshot stays 1."""
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")

    tx = create_transaction(
        user=user,
        account=account,
        type="expense",
        amount=Decimal("50.00000000"),
        currency_code="USD",
        category_id=None,
        date=date.today(),
        fx_rate_override=Decimal("99.00000000"),
    )

    assert tx.fx_rate_snapshot == Decimal("1")
    assert tx.amount_base == Decimal("50.00000000")


@pytest.mark.django_db
def test_update_transaction_fx_rate_override(db):
    """update_transaction accepts fx_rate_override when amount changes."""
    user = UserFactory()
    user.default_currency_code = "TRY"
    user.save()
    CurrencyFactory(code="USD")
    CurrencyFactory(code="TRY")
    account = AccountFactory(user=user, currency_code="USD")
    tx = TransactionFactory(
        user=user,
        account=account,
        currency_code="USD",
        base_currency="TRY",
        amount=Decimal("10.00000000"),
        amount_base=Decimal("330.00000000"),
        fx_rate_snapshot=Decimal("33.00000000"),
        date=date.today(),
    )

    updated = update_transaction(
        transaction=tx,
        user=user,
        amount=Decimal("20.00000000"),
        fx_rate_override=Decimal("35.00000000"),
    )

    assert updated.fx_rate_snapshot == Decimal("35.00000000")
    assert updated.amount_base == Decimal("700.00000000")
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py::test_create_transaction_fx_rate_override_skips_convert -v
```

Expected: `FAILED` with `TypeError: create_transaction() got an unexpected keyword argument 'fx_rate_override'`

- [ ] **Step 3: Implement fx_rate_override in `backend/apps/transactions/services.py`**

Replace `_compute_fx` and update `create_transaction` + `update_transaction` signatures:

```python
def _compute_fx(
    *,
    amount: Decimal,
    currency_code: str,
    base_currency: str,
    tx_date: date_type,
    fx_rate_override: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Return (amount_base, fx_rate_snapshot). Short-circuits when currencies match."""
    if currency_code == base_currency:
        return amount, Decimal("1")
    if fx_rate_override is not None:
        return (amount * fx_rate_override).quantize(QUANTIZE), fx_rate_override
    rate = get_exchange_rate(currency_code, base_currency, at=tx_date)
    return (amount * rate).quantize(QUANTIZE), rate


def create_transaction(
    *,
    user: AbstractBaseUser,
    account: Any,
    type: str,
    amount: Decimal,
    currency_code: str,
    category_id: int | None,
    date: date_type,
    description: str = "",
    reference: str = "",
    fx_rate_override: Decimal | None = None,
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
        fx_rate_override=fx_rate_override,
    )

    return cast(
        Transaction,
        Transaction.objects.create(
            user=user,
            account=account,
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
        ),
    )


def update_transaction(
    *,
    transaction: Transaction,
    user: AbstractBaseUser,
    fx_rate_override: Decimal | None = None,
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
            fx_rate_override=fx_rate_override,
        )

    transaction.save()
    return transaction
```

- [ ] **Step 4: Run tests to verify pass**

```bash
docker compose exec backend pytest apps/transactions/tests/test_services.py -v
```

Expected: All existing tests PASS + 3 new tests PASS

- [ ] **Step 5: Verify no ruff or mypy issues**

```bash
docker compose exec backend ruff check apps/transactions/services.py
docker compose exec backend mypy apps/transactions/services.py
```

Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add backend/apps/transactions/services.py backend/apps/transactions/tests/test_services.py
git commit -m "feat: add fx_rate_override to create/update_transaction (D-012)"
```

---

## Task 2: App Scaffold — exceptions, dirs, INSTALLED_APPS, base URLs

**Files:**
- Modify: `backend/common/exceptions.py`
- Modify: `backend/config/settings/base.py`
- Create: `backend/apps/budgets/__init__.py`
- Create: `backend/apps/budgets/apps.py`
- Create: `backend/apps/budgets/migrations/__init__.py`
- Create: `backend/apps/budgets/tests/__init__.py`

- [ ] **Step 1: Add exceptions to `backend/common/exceptions.py`**

After the `RecurringTemplateInvalidError` class, add:

```python
class BudgetNotFoundError(LookupError):
    """Requested budget does not exist or belongs to another user."""


class BudgetInvalidError(ValueError):
    """Budget configuration is invalid (e.g. date_to < date_from, category not owned)."""
```

- [ ] **Step 2: Create app files**

`backend/apps/budgets/__init__.py` — empty file.

`backend/apps/budgets/apps.py`:
```python
from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.budgets"
```

`backend/apps/budgets/migrations/__init__.py` — empty file.

`backend/apps/budgets/tests/__init__.py` — empty file.

- [ ] **Step 3: Register app in `backend/config/settings/base.py`**

In the `LOCAL_APPS` list, add `"apps.budgets"` after `"apps.recurring"`:

```python
LOCAL_APPS: Final[list[str]] = [
    "common",
    "apps.users",
    "apps.currencies",
    "apps.categories",
    "apps.transactions",
    "apps.accounts",
    "apps.debts",
    "apps.recurring",
    "apps.budgets",
]
```

- [ ] **Step 4: Verify Django recognizes the app**

```bash
docker compose exec backend python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

---

## Task 3: Budget Model + Factory + Migration

**Files:**
- Create: `backend/apps/budgets/models.py`
- Create: `backend/apps/budgets/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/budgets/tests/factories.py`

- [ ] **Step 1: Write model constraint tests**

Create `backend/apps/budgets/tests/test_services.py`:

```python
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.budgets.models import Budget
from apps.budgets.tests.factories import BudgetFactory
from apps.categories.tests.factories import CategoryFactory
from apps.users.tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Model constraint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_model_fields_exist():
    fields = {f.name for f in Budget._meta.get_fields()}
    for field in ["name", "category", "amount", "date_from", "date_to",
                  "alert_threshold", "alert_sent_at", "user", "created_at", "updated_at"]:
        assert field in fields, f"Missing field: {field}"


@pytest.mark.django_db
def test_budget_amount_must_be_positive():
    with pytest.raises(IntegrityError):
        BudgetFactory(amount=Decimal("0.00000000"))


@pytest.mark.django_db
def test_budget_date_to_before_date_from_raises():
    with pytest.raises(IntegrityError):
        BudgetFactory(
            date_from=date(2026, 5, 31),
            date_to=date(2026, 5, 1),
        )


@pytest.mark.django_db
def test_budget_alert_threshold_above_one_raises():
    with pytest.raises(IntegrityError):
        BudgetFactory(alert_threshold=Decimal("1.10000000"))


@pytest.mark.django_db
def test_budget_alert_threshold_negative_raises():
    with pytest.raises(IntegrityError):
        BudgetFactory(alert_threshold=Decimal("-0.10000000"))


@pytest.mark.django_db
def test_budget_alert_threshold_can_be_null():
    b = BudgetFactory(alert_threshold=None)
    assert b.alert_threshold is None


@pytest.mark.django_db
def test_budget_category_can_be_null():
    b = BudgetFactory(category=None)
    assert b.category is None


@pytest.mark.django_db
def test_budget_str():
    b = BudgetFactory(name="Groceries", amount=Decimal("500.00000000"))
    assert "Groceries" in str(b)
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py::test_budget_model_fields_exist -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'apps.budgets.models'`

- [ ] **Step 3: Create `backend/apps/budgets/models.py`**

```python
from __future__ import annotations

from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

User = get_user_model()


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="budgets",
    )
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    date_from = models.DateField()
    date_to = models.DateField()
    alert_threshold = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )
    alert_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="budget_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(date_to__gte=models.F("date_from")),
                name="budget_date_to_gte_date_from",
            ),
            models.CheckConstraint(
                check=(
                    Q(alert_threshold__isnull=True)
                    | Q(alert_threshold__gte=0, alert_threshold__lte=1)
                ),
                name="budget_alert_threshold_valid_range",
            ),
        ]
        indexes: ClassVar = [
            models.Index(fields=["user", "date_from", "date_to"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.amount})"
```

- [ ] **Step 4: Create factory `backend/apps/budgets/tests/factories.py`**

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

import factory

from apps.budgets.models import Budget
from apps.users.tests.factories import UserFactory


class BudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Budget

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Budget {n}")
    category = None
    amount = Decimal("500.00000000")
    date_from = factory.LazyFunction(lambda: date.today().replace(day=1))
    date_to = factory.LazyFunction(lambda: date.today().replace(day=28))
    alert_threshold = None
    alert_sent_at = None
```

- [ ] **Step 5: Generate and run migration**

```bash
docker compose exec backend python manage.py makemigrations budgets
docker compose exec backend python manage.py migrate budgets
```

Expected: `Applying budgets.0001_initial... OK`

- [ ] **Step 6: Run model tests**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -k "model" -v
```

Expected: 8 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/budgets/ backend/common/exceptions.py backend/config/settings/base.py
git commit -m "feat: add Budget model, factory, and initial migration"
```

---

## Task 4: Budget Selectors

**Files:**
- Create: `backend/apps/budgets/selectors.py`
- Modify: `backend/apps/budgets/tests/test_services.py`

- [ ] **Step 1: Write failing selector tests**

Append to `backend/apps/budgets/tests/test_services.py`:

```python
# ---------------------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------------------

from apps.budgets.selectors import get_budget_for_user, get_budget_queryset
from apps.accounts.tests.factories import AccountFactory
from apps.currencies.tests.factories import CurrencyFactory
from apps.transactions.tests.factories import TransactionFactory
from common.exceptions import BudgetNotFoundError


@pytest.mark.django_db
def test_get_budget_queryset_annotates_spent_zero_when_no_transactions():
    user = UserFactory()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(
        user=user,
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )

    qs = get_budget_queryset(user=user)
    result = qs.get(pk=budget.pk)

    assert result.spent == Decimal("0")
    assert result.remaining == budget.amount
    assert result.usage_pct == Decimal("0")


@pytest.mark.django_db
def test_get_budget_queryset_annotates_spent_from_transactions():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        category=None,
    )
    TransactionFactory(
        user=user,
        account=account,
        type="expense",
        amount=Decimal("300.00000000"),
        amount_base=Decimal("300.00000000"),
        base_currency="USD",
        currency_code="USD",
        date=date(2026, 5, 15),
    )

    qs = get_budget_queryset(user=user)
    result = qs.get(pk=budget.pk)

    assert result.spent == Decimal("300.00000000")
    assert result.remaining == Decimal("700.00000000")
    assert result.usage_pct == Decimal("0.30000000")


@pytest.mark.django_db
def test_get_budget_queryset_category_specific_budget_excludes_other_categories():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    cat_food = CategoryFactory(owner=user)
    cat_rent = CategoryFactory(owner=user)
    budget = BudgetFactory(
        user=user,
        amount=Decimal("500.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        category=cat_food,
    )
    # This one should count
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("100.00000000"), amount_base=Decimal("100.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_food, date=date(2026, 5, 10),
    )
    # This one should NOT count (different category)
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("200.00000000"), amount_base=Decimal("200.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_rent, date=date(2026, 5, 10),
    )

    result = get_budget_queryset(user=user).get(pk=budget.pk)

    assert result.spent == Decimal("100.00000000")


@pytest.mark.django_db
def test_get_budget_queryset_null_category_sums_all_categories():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    cat_food = CategoryFactory(owner=user)
    cat_rent = CategoryFactory(owner=user)
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
        category=None,
    )
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("100.00000000"), amount_base=Decimal("100.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_food, date=date(2026, 5, 10),
    )
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("200.00000000"), amount_base=Decimal("200.00000000"),
        currency_code="USD", base_currency="USD",
        category=cat_rent, date=date(2026, 5, 10),
    )

    result = get_budget_queryset(user=user).get(pk=budget.pk)

    assert result.spent == Decimal("300.00000000")


@pytest.mark.django_db
def test_get_budget_queryset_excludes_transactions_outside_date_range():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    budget = BudgetFactory(
        user=user,
        amount=Decimal("500.00000000"),
        date_from=date(2026, 5, 1),
        date_to=date(2026, 5, 31),
    )
    # Outside range — should not count
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("300.00000000"), amount_base=Decimal("300.00000000"),
        currency_code="USD", base_currency="USD",
        date=date(2026, 4, 30),
    )

    result = get_budget_queryset(user=user).get(pk=budget.pk)

    assert result.spent == Decimal("0")


@pytest.mark.django_db
def test_get_budget_queryset_only_returns_requesting_users_budgets():
    user = UserFactory()
    other_user = UserFactory()
    BudgetFactory(user=other_user)
    BudgetFactory(user=user)

    qs = get_budget_queryset(user=user)

    assert qs.count() == 1


@pytest.mark.django_db
def test_get_budget_for_user_raises_not_found_for_other_user():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    with pytest.raises(BudgetNotFoundError):
        get_budget_for_user(user=user, pk=budget.pk)
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -k "selector or get_budget" -v
```

Expected: `FAILED` with `ImportError: cannot import name 'get_budget_for_user'`

- [ ] **Step 3: Create `backend/apps/budgets/selectors.py`**

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    When,
)
from django.db.models.functions import Coalesce

from apps.budgets.models import Budget
from apps.transactions.models import Transaction
from common.exceptions import BudgetNotFoundError

DECIMAL_FIELD = DecimalField(max_digits=20, decimal_places=8)
_ZERO = Decimal("0")


def _spent_annotation() -> Case:
    """
    Returns a Case expression that computes spent amount differently for
    category-specific vs. all-category (null) budgets.

    Only expense transactions within the budget's date range are counted.
    Amounts are taken from amount_base (already in user's base currency).
    """
    category_subq = (
        Transaction.objects.filter(
            user=OuterRef("user"),
            category=OuterRef("category"),
            type="expense",
            date__gte=OuterRef("date_from"),
            date__lte=OuterRef("date_to"),
        )
        .values("user")
        .annotate(total=Sum("amount_base"))
        .values("total")
    )

    all_cats_subq = (
        Transaction.objects.filter(
            user=OuterRef("user"),
            type="expense",
            date__gte=OuterRef("date_from"),
            date__lte=OuterRef("date_to"),
        )
        .values("user")
        .annotate(total=Sum("amount_base"))
        .values("total")
    )

    return Case(
        When(
            category__isnull=True,
            then=Coalesce(Subquery(all_cats_subq), _ZERO, output_field=DECIMAL_FIELD),
        ),
        default=Coalesce(Subquery(category_subq), _ZERO, output_field=DECIMAL_FIELD),
        output_field=DECIMAL_FIELD,
    )


def get_budget_queryset(*, user: Any) -> QuerySet[Budget]:
    spent = _spent_annotation()
    return (
        Budget.objects.filter(user=user)
        .select_related("category")
        .annotate(spent=spent)
        .annotate(
            remaining=ExpressionWrapper(F("amount") - F("spent"), output_field=DECIMAL_FIELD),
            usage_pct=ExpressionWrapper(F("spent") / F("amount"), output_field=DECIMAL_FIELD),
        )
        .order_by("-date_from", "name")
    )


def get_budget_for_user(*, user: Any, pk: int) -> Budget:
    try:
        return cast(Budget, get_budget_queryset(user=user).get(pk=pk))
    except Budget.DoesNotExist:
        raise BudgetNotFoundError(f"Budget {pk} not found.") from None


def get_all_active_budgets_for_alert(*, today: date) -> QuerySet[Budget]:
    """
    Returns budgets that are currently active (date range includes today),
    have an alert threshold set, and have not yet been alerted this period.
    """
    spent = _spent_annotation()
    return (
        Budget.objects.filter(
            date_from__lte=today,
            date_to__gte=today,
            alert_threshold__isnull=False,
            alert_sent_at__isnull=True,
        )
        .select_related("user", "category")
        .annotate(spent=spent)
        .annotate(
            usage_pct=ExpressionWrapper(F("spent") / F("amount"), output_field=DECIMAL_FIELD),
        )
    )
```

- [ ] **Step 4: Run selector tests**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -v
```

Expected: All model + selector tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/budgets/selectors.py backend/apps/budgets/tests/test_services.py
git commit -m "feat: add Budget selectors with Subquery-based spent annotation"
```

---

## Task 5: Budget Services (create / update / delete)

**Files:**
- Create: `backend/apps/budgets/services.py`
- Modify: `backend/apps/budgets/tests/test_services.py`

- [ ] **Step 1: Write failing service tests**

Append to `backend/apps/budgets/tests/test_services.py`:

```python
# ---------------------------------------------------------------------------
# Service tests — create_budget
# ---------------------------------------------------------------------------

from apps.budgets.services import create_budget, delete_budget, update_budget
from common.exceptions import BudgetInvalidError


@pytest.mark.django_db
def test_create_budget_happy_path():
    user = UserFactory()

    budget = create_budget(user=user, data={
        "name": "Groceries",
        "category": None,
        "amount": Decimal("500.00000000"),
        "date_from": date(2026, 5, 1),
        "date_to": date(2026, 5, 31),
        "alert_threshold": Decimal("0.80000000"),
    })

    assert budget.pk is not None
    assert budget.name == "Groceries"
    assert budget.user == user


@pytest.mark.django_db
def test_create_budget_date_to_before_date_from_raises():
    user = UserFactory()

    with pytest.raises(BudgetInvalidError, match="date_to"):
        create_budget(user=user, data={
            "name": "Bad dates",
            "category": None,
            "amount": Decimal("100.00000000"),
            "date_from": date(2026, 5, 31),
            "date_to": date(2026, 5, 1),
        })


@pytest.mark.django_db
def test_create_budget_category_not_owned_raises():
    user = UserFactory()
    other = UserFactory()
    cat = CategoryFactory(owner=other)

    with pytest.raises(BudgetInvalidError, match="category"):
        create_budget(user=user, data={
            "name": "Bad category",
            "category_id": cat.pk,
            "amount": Decimal("100.00000000"),
            "date_from": date(2026, 5, 1),
            "date_to": date(2026, 5, 31),
        })


# ---------------------------------------------------------------------------
# Service tests — update_budget
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_update_budget_changes_name():
    user = UserFactory()
    budget = BudgetFactory(user=user, name="Old")

    updated = update_budget(budget=budget, data={"name": "New"})

    assert updated.name == "New"


@pytest.mark.django_db
def test_update_budget_resets_alert_sent_at_when_amount_changes():
    from django.utils import timezone

    user = UserFactory()
    budget = BudgetFactory(
        user=user,
        amount=Decimal("500.00000000"),
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=timezone.now(),
    )

    updated = update_budget(budget=budget, data={"amount": Decimal("1000.00000000")})

    assert updated.alert_sent_at is None


@pytest.mark.django_db
def test_update_budget_resets_alert_sent_at_when_threshold_changes():
    from django.utils import timezone

    user = UserFactory()
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=timezone.now(),
    )

    updated = update_budget(budget=budget, data={"alert_threshold": Decimal("0.90000000")})

    assert updated.alert_sent_at is None


@pytest.mark.django_db
def test_update_budget_does_not_reset_alert_sent_at_when_name_only_changes():
    from django.utils import timezone

    user = UserFactory()
    sent_at = timezone.now()
    budget = BudgetFactory(user=user, alert_threshold=Decimal("0.80000000"), alert_sent_at=sent_at)

    updated = update_budget(budget=budget, data={"name": "Renamed"})

    assert updated.alert_sent_at == sent_at


# ---------------------------------------------------------------------------
# Service tests — delete_budget
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_budget_removes_record():
    user = UserFactory()
    budget = BudgetFactory(user=user)
    pk = budget.pk

    delete_budget(budget=budget)

    assert not Budget.objects.filter(pk=pk).exists()
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -k "service or create_budget or update_budget or delete_budget" -v
```

Expected: `FAILED` with `ImportError: cannot import name 'create_budget'`

- [ ] **Step 3: Create `backend/apps/budgets/services.py`**

```python
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction as db_transaction
from django.utils import timezone

from apps.budgets.models import Budget
from common.exceptions import BudgetInvalidError, BudgetNotFoundError


def _validate_dates(date_from: Any, date_to: Any) -> None:
    if date_from is not None and date_to is not None and date_to < date_from:
        raise BudgetInvalidError("date_to must be on or after date_from.")


def _validate_category_ownership(*, category_id: int | None, user: Any) -> Any:
    if category_id is None:
        return None
    from apps.categories.models import Category
    from django.db.models import Q
    try:
        return Category.objects.get(Q(is_system=True) | Q(owner=user), pk=category_id)
    except Category.DoesNotExist:
        raise BudgetInvalidError(
            f"category {category_id} not found or not accessible."
        ) from None


def create_budget(*, user: Any, data: dict[str, Any]) -> Budget:
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    _validate_dates(date_from, date_to)

    category_id = data.pop("category_id", None)
    category = data.pop("category", None)
    if category_id is not None:
        category = _validate_category_ownership(category_id=category_id, user=user)

    return Budget.objects.create(user=user, category=category, **data)


def update_budget(*, budget: Budget, data: dict[str, Any]) -> Budget:
    effective_from = data.get("date_from", budget.date_from)
    effective_to = data.get("date_to", budget.date_to)
    _validate_dates(effective_from, effective_to)

    category_id = data.pop("category_id", None)
    if category_id is not None:
        data["category"] = _validate_category_ownership(category_id=category_id, user=budget.user)

    amount_changed = "amount" in data
    threshold_changed = "alert_threshold" in data

    for attr, value in data.items():
        setattr(budget, attr, value)

    if amount_changed or threshold_changed:
        budget.alert_sent_at = None

    budget.save()
    return budget


def delete_budget(*, budget: Budget) -> None:
    budget.delete()


def check_and_send_budget_alerts(*, budget: Budget) -> bool:
    """
    Checks if budget has crossed its alert threshold. Idempotent: returns False
    if alert already sent or threshold not configured. Returns True if email sent.
    """
    if budget.alert_threshold is None:
        return False
    if budget.alert_sent_at is not None:
        return False

    usage_pct: Decimal = getattr(budget, "usage_pct", Decimal("0"))
    if usage_pct < budget.alert_threshold:
        return False

    from django.conf import settings
    from django.core.mail import send_mail

    with db_transaction.atomic():
        Budget.objects.filter(pk=budget.pk).update(alert_sent_at=timezone.now())

    send_mail(
        subject=f"[Ledgr] Budget Alert: {budget.name}",
        message=(
            f"Your budget '{budget.name}' has reached "
            f"{float(usage_pct) * 100:.1f}% of its limit.\n\n"
            f"Spent: {getattr(budget, 'spent', '?')} / {budget.amount} "
            f"{budget.user.default_currency_code}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[budget.user.email],
        fail_silently=True,
    )

    return True
```

- [ ] **Step 4: Run all service tests**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/budgets/services.py backend/apps/budgets/tests/test_services.py
git commit -m "feat: add Budget services (create, update, delete, alert check)"
```

---

## Task 6: Alert Service Tests

**Files:**
- Modify: `backend/apps/budgets/tests/test_services.py`

- [ ] **Step 1: Write alert service tests**

Append to `backend/apps/budgets/tests/test_services.py`:

```python
# ---------------------------------------------------------------------------
# Alert service tests
# ---------------------------------------------------------------------------

from unittest.mock import patch

from apps.budgets.services import check_and_send_budget_alerts


@pytest.mark.django_db
def test_alert_not_sent_when_threshold_is_none():
    user = UserFactory()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(user=user, alert_threshold=None)
    budget.usage_pct = Decimal("0.90000000")

    result = check_and_send_budget_alerts(budget=budget)

    assert result is False


@pytest.mark.django_db
def test_alert_not_sent_when_already_sent():
    from django.utils import timezone

    user = UserFactory()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=timezone.now(),
    )
    budget.usage_pct = Decimal("0.95000000")

    result = check_and_send_budget_alerts(budget=budget)

    assert result is False


@pytest.mark.django_db
def test_alert_not_sent_when_below_threshold():
    user = UserFactory()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(user=user, alert_threshold=Decimal("0.80000000"))
    budget.usage_pct = Decimal("0.70000000")

    result = check_and_send_budget_alerts(budget=budget)

    assert result is False


@pytest.mark.django_db
def test_alert_sent_when_at_threshold_boundary():
    user = UserFactory()
    user.email = "test@ledgr.io"
    user.save()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    budget.usage_pct = Decimal("0.80000000")
    budget.spent = Decimal("400.00000000")

    with patch("apps.budgets.services.send_mail") as mock_mail:
        result = check_and_send_budget_alerts(budget=budget)

    assert result is True
    mock_mail.assert_called_once()
    refreshed = Budget.objects.get(pk=budget.pk)
    assert refreshed.alert_sent_at is not None


@pytest.mark.django_db
def test_alert_idempotent_second_call_skipped():
    user = UserFactory()
    CurrencyFactory(code="USD")
    budget = BudgetFactory(
        user=user,
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    budget.usage_pct = Decimal("0.90000000")
    budget.spent = Decimal("450.00000000")

    with patch("apps.budgets.services.send_mail"):
        check_and_send_budget_alerts(budget=budget)

    # Simulate second task run: reload from DB (alert_sent_at is now set)
    budget_reloaded = Budget.objects.get(pk=budget.pk)
    budget_reloaded.usage_pct = Decimal("0.90000000")

    with patch("apps.budgets.services.send_mail") as mock_mail_2:
        result = check_and_send_budget_alerts(budget=budget_reloaded)

    assert result is False
    mock_mail_2.assert_not_called()
```

- [ ] **Step 2: Run alert tests**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -k "alert" -v
```

Expected: All 5 alert tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/apps/budgets/tests/test_services.py
git commit -m "test: add alert service idempotency tests for Budget"
```

---

## Task 7: Serializers + Views + URLs + View Tests

**Files:**
- Create: `backend/apps/budgets/serializers.py`
- Create: `backend/apps/budgets/views.py`
- Create: `backend/apps/budgets/urls.py`
- Modify: `backend/config/urls.py`
- Create: `backend/apps/budgets/tests/test_views.py`

- [ ] **Step 1: Write failing view tests**

Create `backend/apps/budgets/tests/test_views.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import AccountFactory
from apps.budgets.models import Budget
from apps.budgets.tests.factories import BudgetFactory
from apps.categories.tests.factories import CategoryFactory
from apps.currencies.tests.factories import CurrencyFactory
from apps.transactions.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory


def _auth_client(user) -> APIClient:
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# ---------------------------------------------------------------------------
# GET /api/v1/budgets/ — list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_list_happy_path():
    user = UserFactory()
    CurrencyFactory(code="USD")
    BudgetFactory(user=user, name="Food")
    BudgetFactory(user=user, name="Rent")

    response = _auth_client(user).get("/api/v1/budgets/")

    assert response.status_code == 200
    assert response.data["count"] == 2
    result = response.data["results"][0]
    assert "spent" in result
    assert "remaining" in result
    assert "usage_pct" in result


@pytest.mark.django_db
def test_budget_list_auth_guard():
    response = APIClient().get("/api/v1/budgets/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_budget_list_only_own_budgets():
    user = UserFactory()
    other = UserFactory()
    BudgetFactory(user=user)
    BudgetFactory(user=other)

    response = _auth_client(user).get("/api/v1/budgets/")

    assert response.data["count"] == 1


# ---------------------------------------------------------------------------
# POST /api/v1/budgets/ — create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_create_happy_path():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "Groceries",
        "amount": "500.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
    }, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "Groceries"
    assert response.data["spent"] == "0.00000000"
    assert Budget.objects.filter(user=user, name="Groceries").exists()


@pytest.mark.django_db
def test_budget_create_auth_guard():
    response = APIClient().post("/api/v1/budgets/", {
        "name": "X", "amount": "100", "date_from": "2026-05-01", "date_to": "2026-05-31"
    }, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_budget_create_invalid_dates():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "Bad",
        "amount": "100.00000000",
        "date_from": "2026-05-31",
        "date_to": "2026-05-01",
    }, format="json")

    assert response.status_code == 400
    assert response.data["error"]["type"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_budget_create_negative_amount_rejected():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "X",
        "amount": "-100.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
    }, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_budget_create_threshold_above_one_rejected():
    user = UserFactory()

    response = _auth_client(user).post("/api/v1/budgets/", {
        "name": "X",
        "amount": "500.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
        "alert_threshold": "1.50000000",
    }, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_budget_create_with_spent_returns_correct_usage():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")

    _auth_client(user).post("/api/v1/budgets/", {
        "name": "Food",
        "amount": "1000.00000000",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
    }, format="json")

    budget = Budget.objects.get(user=user, name="Food")
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("300.00000000"), amount_base=Decimal("300.00000000"),
        currency_code="USD", base_currency="USD", date=date(2026, 5, 10),
    )

    response = _auth_client(user).get(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 200
    assert Decimal(response.data["spent"]) == Decimal("300.00000000")
    assert Decimal(response.data["usage_pct"]) == Decimal("0.30000000")


# ---------------------------------------------------------------------------
# GET /api/v1/budgets/<pk>/ — detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_detail_ownership():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    response = _auth_client(user).get(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/budgets/<pk>/ — update
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_update_happy_path():
    user = UserFactory()
    budget = BudgetFactory(user=user, name="Old Name")

    response = _auth_client(user).patch(
        f"/api/v1/budgets/{budget.pk}/", {"name": "New Name"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "New Name"


@pytest.mark.django_db
def test_budget_update_ownership():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    response = _auth_client(user).patch(
        f"/api/v1/budgets/{budget.pk}/", {"name": "Hack"}, format="json"
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/budgets/<pk>/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_budget_delete_happy_path():
    user = UserFactory()
    budget = BudgetFactory(user=user)

    response = _auth_client(user).delete(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 204
    assert not Budget.objects.filter(pk=budget.pk).exists()


@pytest.mark.django_db
def test_budget_delete_ownership():
    user = UserFactory()
    other = UserFactory()
    budget = BudgetFactory(user=other)

    response = _auth_client(user).delete(f"/api/v1/budgets/{budget.pk}/")

    assert response.status_code == 404
    assert Budget.objects.filter(pk=budget.pk).exists()
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose exec backend pytest apps/budgets/tests/test_views.py::test_budget_list_auth_guard -v
```

Expected: `FAILED` — 404 (URL not registered yet)

- [ ] **Step 3: Create `backend/apps/budgets/serializers.py`**

```python
from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from rest_framework import serializers

from apps.budgets.models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    spent = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True, default=Decimal("0")
    )
    remaining = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True, default=Decimal("0")
    )
    usage_pct = serializers.DecimalField(
        max_digits=20, decimal_places=8, read_only=True, default=Decimal("0")
    )

    class Meta:
        model = Budget
        fields: ClassVar = [
            "id",
            "name",
            "category",
            "amount",
            "date_from",
            "date_to",
            "alert_threshold",
            "alert_sent_at",
            "spent",
            "remaining",
            "usage_pct",
            "created_at",
            "updated_at",
        ]
        read_only_fields: ClassVar = [
            "id",
            "alert_sent_at",
            "spent",
            "remaining",
            "usage_pct",
            "created_at",
            "updated_at",
        ]


class BudgetCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    category_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=8, min_value=Decimal("0.00000001")
    )
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    alert_threshold = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        allow_null=True,
        required=False,
        default=None,
        min_value=Decimal("0"),
        max_value=Decimal("1"),
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["date_to"] < data["date_from"]:
            raise serializers.ValidationError(
                {"date_to": "date_to must be on or after date_from."}
            )
        return data


class BudgetUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    category_id = serializers.IntegerField(allow_null=True, required=False)
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=8, min_value=Decimal("0.00000001"), required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    alert_threshold = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        allow_null=True,
        required=False,
        min_value=Decimal("0"),
        max_value=Decimal("1"),
    )
```

- [ ] **Step 4: Create `backend/apps/budgets/views.py`**

```python
from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import BudgetInvalidError, BudgetNotFoundError

from . import selectors, services
from .serializers import BudgetCreateSerializer, BudgetSerializer, BudgetUpdateSerializer


class BudgetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BudgetListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        qs = selectors.get_budget_queryset(user=user)
        paginator = BudgetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(BudgetSerializer(page, many=True).data)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = BudgetCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            budget = services.create_budget(user=user, data=dict(serializer.validated_data))
        except BudgetInvalidError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        detail = selectors.get_budget_for_user(user=user, pk=budget.pk)
        return Response(BudgetSerializer(detail).data, status=status.HTTP_201_CREATED)


class BudgetDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_404(self, pk: int, user: AbstractBaseUser) -> object:
        try:
            return selectors.get_budget_for_user(user=user, pk=pk)
        except BudgetNotFoundError as exc:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail=str(exc)) from exc

    def get(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        budget = self._get_or_404(pk, user)
        return Response(BudgetSerializer(budget).data)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        budget = self._get_or_404(pk, user)
        serializer = BudgetUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = services.update_budget(
                budget=budget,  # type: ignore[arg-type]
                data=dict(serializer.validated_data),
            )
        except BudgetInvalidError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        detail = selectors.get_budget_for_user(user=user, pk=updated.pk)
        return Response(BudgetSerializer(detail).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        budget = self._get_or_404(pk, user)
        services.delete_budget(budget=budget)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Create `backend/apps/budgets/urls.py`**

```python
from __future__ import annotations

from django.urls import URLPattern, path

from .views import BudgetDetailView, BudgetListCreateView

urlpatterns: list[URLPattern] = [
    path("", BudgetListCreateView.as_view(), name="budget-list-create"),
    path("<int:pk>/", BudgetDetailView.as_view(), name="budget-detail"),
]
```

- [ ] **Step 6: Register URL in `backend/config/urls.py`**

Add `path("budgets/", include("apps.budgets.urls")),` after the `recurring/` line:

```python
api_v1_patterns: list[URLPattern | URLResolver] = [
    path("", include("common.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.currencies.urls")),
    path("", include("apps.categories.urls")),
    path("", include("apps.transactions.urls")),
    path("", include("apps.accounts.urls")),
    path("debts/", include("apps.debts.urls")),
    path("recurring/", include("apps.recurring.urls")),
    path("budgets/", include("apps.budgets.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
```

- [ ] **Step 7: Run all view tests**

```bash
docker compose exec backend pytest apps/budgets/tests/test_views.py -v
```

Expected: All 15 view tests PASS

- [ ] **Step 8: Run full budget test suite**

```bash
docker compose exec backend pytest apps/budgets/ -v
```

Expected: All tests PASS

- [ ] **Step 9: Check ruff and mypy**

```bash
docker compose exec backend ruff check apps/budgets/
docker compose exec backend mypy apps/budgets/
```

Expected: 0 errors each

- [ ] **Step 10: Commit**

```bash
git add backend/apps/budgets/serializers.py backend/apps/budgets/views.py \
        backend/apps/budgets/urls.py backend/config/urls.py \
        backend/apps/budgets/tests/test_views.py
git commit -m "feat: add Budget serializers, views, and URL routing"
```

---

## Task 8: Beat Task + Data Migration

**Files:**
- Create: `backend/apps/budgets/tasks.py`
- Create: `backend/apps/budgets/migrations/0002_register_budget_alert_beat.py`
- Modify: `backend/apps/budgets/tests/test_services.py`

- [ ] **Step 1: Write task test**

Append to `backend/apps/budgets/tests/test_services.py`:

```python
# ---------------------------------------------------------------------------
# Beat task test
# ---------------------------------------------------------------------------

from unittest.mock import patch

from apps.budgets.tasks import send_budget_alerts


@pytest.mark.django_db
def test_send_budget_alerts_task_skips_when_below_threshold():
    user = UserFactory()
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    today = date.today()
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=today.replace(day=1),
        date_to=today.replace(day=28),
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    # 30% spent — below 80% threshold
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("300.00000000"), amount_base=Decimal("300.00000000"),
        currency_code="USD", base_currency="USD", date=today,
    )

    with patch("apps.budgets.services.send_mail") as mock_mail:
        result = send_budget_alerts()

    assert result["sent"] == 0
    mock_mail.assert_not_called()


@pytest.mark.django_db
def test_send_budget_alerts_task_sends_when_above_threshold():
    user = UserFactory()
    user.email = "owner@ledgr.io"
    user.default_currency_code = "USD"
    user.save()
    CurrencyFactory(code="USD")
    account = AccountFactory(user=user, currency_code="USD")
    today = date.today()
    budget = BudgetFactory(
        user=user,
        amount=Decimal("1000.00000000"),
        date_from=today.replace(day=1),
        date_to=today.replace(day=28),
        alert_threshold=Decimal("0.80000000"),
        alert_sent_at=None,
    )
    # 90% spent — above threshold
    TransactionFactory(
        user=user, account=account, type="expense",
        amount=Decimal("900.00000000"), amount_base=Decimal("900.00000000"),
        currency_code="USD", base_currency="USD", date=today,
    )

    with patch("apps.budgets.services.send_mail") as mock_mail:
        result = send_budget_alerts()

    assert result["sent"] == 1
    mock_mail.assert_called_once()
    assert Budget.objects.get(pk=budget.pk).alert_sent_at is not None
```

- [ ] **Step 2: Run to verify failure**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py::test_send_budget_alerts_task_skips_when_below_threshold -v
```

Expected: `FAILED` with `ImportError: cannot import name 'send_budget_alerts'`

- [ ] **Step 3: Create `backend/apps/budgets/tasks.py`**

```python
from __future__ import annotations

from datetime import date

from celery import shared_task
from django.db.utils import OperationalError


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=5,
)
def send_budget_alerts(target_date_iso: str | None = None) -> dict[str, int]:
    """
    Beat-scheduled daily at 07:00 UTC.
    Checks all active budgets with an alert threshold and sends email if threshold crossed.
    """
    from apps.budgets.selectors import get_all_active_budgets_for_alert
    from apps.budgets.services import check_and_send_budget_alerts

    today = date.fromisoformat(target_date_iso) if target_date_iso else date.today()
    budgets = list(get_all_active_budgets_for_alert(today=today))

    sent = 0
    for budget in budgets:
        if check_and_send_budget_alerts(budget=budget):
            sent += 1

    return {"sent": sent, "checked": len(budgets)}
```

- [ ] **Step 4: Run task tests**

```bash
docker compose exec backend pytest apps/budgets/tests/test_services.py -k "task or send_budget_alerts" -v
```

Expected: Both task tests PASS

- [ ] **Step 5: Create beat registration migration `backend/apps/budgets/migrations/0002_register_budget_alert_beat.py`**

```python
"""Register the daily budget alert task as a periodic task in Celery beat."""
from __future__ import annotations

import json

from django.db import migrations


def register_forwards(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="7",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )
    PeriodicTask.objects.update_or_create(
        name="apps.budgets.tasks.send_budget_alerts",
        defaults={
            "task": "apps.budgets.tasks.send_budget_alerts",
            "crontab": schedule,
            "kwargs": json.dumps({}),
            "enabled": True,
            "description": "Sends budget threshold alert emails daily at 07:00 UTC.",
        },
    )


def register_backwards(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task="apps.budgets.tasks.send_budget_alerts"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("budgets", "0001_initial"),
        ("django_celery_beat", "0018_improve_crontab_helptext"),
    ]

    operations = [
        migrations.RunPython(register_forwards, register_backwards),
    ]
```

- [ ] **Step 6: Run migration**

```bash
docker compose exec backend python manage.py migrate budgets
```

Expected: `Applying budgets.0002_register_budget_alert_beat... OK`

- [ ] **Step 7: Run full test suite**

```bash
docker compose exec backend pytest apps/budgets/ -v
```

Expected: All tests PASS

- [ ] **Step 8: Run project-wide quality checks**

```bash
docker compose exec backend pytest --cov=. --cov-report=term-missing --cov-fail-under=80
docker compose exec backend ruff check .
docker compose exec backend mypy .
```

Expected: Coverage ≥ 80%, ruff: 0 issues, mypy: 0 errors

- [ ] **Step 9: Commit**

```bash
git add backend/apps/budgets/tasks.py \
        backend/apps/budgets/migrations/0002_register_budget_alert_beat.py \
        backend/apps/budgets/tests/test_services.py
git commit -m "feat: add send_budget_alerts Celery beat task and beat migration (07:00 UTC)"
```

---

## Task 9: Final Verification + CLAUDE.md Update

- [ ] **Step 1: Smoke test — create a budget via curl**

```bash
# Register + login to get token (substitute with your dev credentials)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@ledgr.io","password":"DevPass123!"}' | python -m json.tool | grep access | awk -F'"' '{print $4}')

curl -s -X POST http://localhost:8000/api/v1/budgets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Budget","amount":"1000.00","date_from":"2026-05-01","date_to":"2026-05-31"}' \
  | python -m json.tool
```

Expected: 201 with `id`, `spent: "0.00000000"`, `usage_pct: "0.00000000"`

- [ ] **Step 2: Verify Swagger shows budget endpoints**

Open `http://localhost:8000/api/v1/docs/` and confirm `GET/POST /api/v1/budgets/` and `GET/PATCH/DELETE /api/v1/budgets/{pk}/` are listed.

- [ ] **Step 3: Update CLAUDE.md**

In both `CLAUDE.md` files, update:

**Current State block:**
```markdown
| **Active Phase** | 6 — Frontend skeleton + Auth |
| **Last Completed** | Phase 5 — Budgets + Alerts (2026-05-01) |
| **Next Action** | Phase 6 plan: Vite/React/TS skeleton, auth flow |
| **Open Decisions** | None |
```

**Phase Plan table** — mark Phase 5 as ✅:
```markdown
| **5. Budgets + Alerts** | ✅ Done | Category-based, date_from/date_to, Subquery usage, Celery beat 07:00 UTC. D-012 fx_rate_override. N tests, X% cov |
```

**Testing Standards block** — update test count and coverage after final run.

**Endpoints (live)** — add:
```
- Budgets: `GET/POST /api/v1/budgets/` · `GET/PATCH/DELETE /api/v1/budgets/<pk>/`
```

- [ ] **Step 4: Tag and commit**

```bash
git add CLAUDE.md .claude/CLAUDE.md
git commit -m "docs: update CLAUDE.md for Phase 5 completion"
git tag phase-5-complete
```

---

## Self-Review Checklist

**Spec coverage:**

| Spec requirement | Covered by task |
|---|---|
| Budget model with all fields | Task 3 |
| `date_to >= date_from` constraint | Task 3 (model + Task 7 view validation) |
| `alert_threshold` 0–1 constraint | Task 3 |
| `category=null` means all categories | Task 4 (selector Case/When) |
| `spent` via Subquery (§11) | Task 4 |
| `remaining` + `usage_pct` annotated | Task 4 |
| `create_budget` validates category ownership | Task 5 |
| `update_budget` resets `alert_sent_at` on amount/threshold change | Task 5 |
| `check_and_send_budget_alerts` idempotency | Task 5 + Task 6 |
| Alert at boundary (usage_pct == threshold) | Task 6 |
| 5-type tests for financial endpoint | Task 7 (list/create/detail/update/delete) |
| Beat task at 07:00 UTC via data migration | Task 8 |
| D-012 `fx_rate_override` | Task 1 |
| `docs/decisions.md` D-012 closed | Done before plan (session) |

**Placeholder scan:** No TBD, TODO, or placeholder patterns found.

**Type consistency:** All function names consistent across tasks (`create_budget`, `update_budget`, `delete_budget`, `check_and_send_budget_alerts`, `get_budget_queryset`, `get_budget_for_user`, `get_all_active_budgets_for_alert`, `send_budget_alerts`).
