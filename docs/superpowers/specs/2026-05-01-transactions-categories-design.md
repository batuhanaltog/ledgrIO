# Phase 4: Transactions + Categories — Design Spec

**Date:** 2026-05-01  
**Status:** Approved  
**Scope:** `apps/categories/` + `apps/transactions/` — income/expense tracking with multi-currency snapshot, unlimited category hierarchy, and comprehensive reporting.

---

## 1. Architecture

Two separate Django apps with a clear dependency direction: `transactions` depends on `categories`, not the other way around.

```
apps/
├── categories/     # Category tree — shared by transactions (Phase 4) and budgets (Phase 5)
│   ├── models.py
│   ├── services.py
│   ├── selectors.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   └── tests/
└── transactions/   # Income/expense transactions with FX snapshot
    ├── models.py
    ├── services.py
    ├── selectors.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── migrations/
    └── tests/
```

Both apps follow the established service pattern: models hold data, services own all writes, selectors own all reads, views handle request/response only.

---

## 2. Data Models

### `Category` (`apps/categories/models.py`)

```python
class Category(TimestampedModel, SoftDeleteModel):
    name      = CharField(max_length=100)
    icon      = CharField(max_length=50, blank=True)   # emoji or icon key
    color     = CharField(max_length=7, blank=True)    # hex (#FF5733)
    parent    = ForeignKey("self", null=True, blank=True, on_delete=PROTECT)
    owner     = ForeignKey(User, null=True, blank=True, on_delete=CASCADE)
    is_system = BooleanField(default=False)
    ordering  = IntegerField(default=0)
```

**Ownership rules:**
- `owner=null, is_system=True` → admin seed, immutable by users
- `owner=User, is_system=False` → user-owned, visible/editable only by owner
- A user may add their own child categories under system categories (`parent=system_cat, owner=user`)

**Constraints:**
- Max hierarchy depth: 10 levels (enforced in service, not DB)
- No cycles: service validates the parent chain before save
- `parent` FK uses `on_delete=PROTECT` — a category with children cannot be deleted until all children are removed or reassigned first
- Soft delete via `SoftDeleteModel`; linked transactions become `category=null` via `SET_NULL`

**Migrations:**
- `0001_initial.py` — model + indexes
- `0002_seed_system_categories.py` — admin seed (e.g. Food, Transport, Health, Entertainment, Income, Other)

---

### `Transaction` (`apps/transactions/models.py`)

```python
class Transaction(TimestampedModel, SoftDeleteModel):
    user             = ForeignKey(User, on_delete=CASCADE)
    type             = CharField(max_length=10, choices=["income", "expense"])
    amount           = DecimalField(max_digits=20, decimal_places=8)  # original currency
    currency_code    = CharField(max_length=10)                        # original currency
    amount_base      = DecimalField(max_digits=20, decimal_places=8)  # user default currency
    base_currency    = CharField(max_length=10)                        # user default currency code
    fx_rate_snapshot = DecimalField(max_digits=20, decimal_places=8)  # rate at transaction time
    category         = ForeignKey(Category, null=True, on_delete=SET_NULL)
    date             = DateField(db_index=True)
    description      = TextField(blank=True)
    reference        = CharField(max_length=255, blank=True)           # invoice number, external ref
```

**Indexes:**
- `(user, date)` — primary filter
- `(user, type)` — income/expense split
- `(user, category_id)` — category summary
- `GinIndex` on `description` — PostgreSQL full-text search

**FX snapshot invariant:** Once written, `amount_base` and `fx_rate_snapshot` never change unless `amount` or `currency_code` is explicitly updated. Historical records are immutable to exchange rate fluctuations.

---

## 3. API Endpoints

### Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/categories/` | System + user categories |
| `POST` | `/api/v1/categories/` | Create user category |
| `PATCH` | `/api/v1/categories/{id}/` | Update user category (system = 403) |
| `DELETE` | `/api/v1/categories/{id}/` | Soft delete (system = 403) |

**Query params for `GET /categories/`:**
- `?format=tree` (default) — nested parent/children structure for sidebar display; system categories listed first, user's own categories follow
- `?format=flat` — flat list with `parent_id` for dropdown/select in forms

**Visibility rule:** All authenticated users see system categories (`is_system=True`). Each user sees only their own user-owned categories (`owner=request.user`). Other users' private categories are invisible.

**Response (tree format):**
```json
[
  {
    "id": 1, "name": "Food", "icon": "🍔", "color": "#4CAF50",
    "is_system": true, "owner": null,
    "children": [
      {"id": 10, "name": "Restaurant", "is_system": false, "owner": 42, "children": []}
    ]
  }
]
```

---

### Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/transactions/` | Filtered + paginated list |
| `POST` | `/api/v1/transactions/` | Create (FX snapshot auto-calculated) |
| `GET` | `/api/v1/transactions/{id}/` | Single transaction detail |
| `PATCH` | `/api/v1/transactions/{id}/` | Update (FX recalculated if amount/currency changes) |
| `DELETE` | `/api/v1/transactions/{id}/` | Soft delete |
| `GET` | `/api/v1/transactions/summary/` | Monthly totals + running balance |

**Filter params for `GET /transactions/`:**
```
?type=expense|income
&category=<id>
&currency=USD
&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
&amount_min=100&amount_max=5000
&search=<text>              # full-text on description
&ordering=-date|date|amount|-amount
&page=1&page_size=20
```

**Transaction response (includes nested category):**
```json
{
  "id": 1,
  "type": "expense",
  "amount": "50.00000000",
  "currency_code": "USD",
  "amount_base": "1650.00000000",
  "base_currency": "TRY",
  "fx_rate_snapshot": "33.00000000",
  "date": "2026-05-01",
  "description": "Weekly groceries",
  "reference": "",
  "category": {
    "id": 42,
    "name": "Market",
    "color": "#4CAF50",
    "icon": "🛒",
    "parent_name": "Food"
  },
  "created_at": "2026-05-01T10:00:00Z"
}
```

**Summary params for `GET /transactions/summary/`:**
```
?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
&group_by=day|week|month    # running_balance granularity (default: day)
```

**Summary response:**
```json
{
  "total_income": "5000.00000000",
  "total_expense": "3200.00000000",
  "net": "1800.00000000",
  "by_category": [
    {"category_id": 1, "category_name": "Food", "total": "800.00000000", "count": 23}
  ],
  "running_balance": [
    {"period": "2026-01", "cumulative_net": "1800.00000000"}
  ]
}
```

---

## 4. Service Layer

### `apps/categories/services.py`

```python
def create_category(*, user, name, parent_id, icon, color, ordering) -> Category
def update_category(*, category, user, **fields) -> Category
def soft_delete_category(*, category, user) -> None
```

**Business rules:**
- `parent_id` validation: resolve category, check user has access (system or own), check depth ≤ 10, check no cycle
- System category (`is_system=True`) → `update`/`delete` raises `CategoryPermissionError`
- Other user's category → raises `CategoryPermissionError`

### `apps/transactions/services.py`

```python
def create_transaction(*, user, type, amount, currency_code, category_id, date, description, reference) -> Transaction
def update_transaction(*, transaction, user, **fields) -> Transaction
def soft_delete_transaction(*, transaction, user) -> None
```

**`create_transaction` flow:**
1. Validate `currency_code` exists → `UnknownCurrencyError`
2. Validate `category_id` accessible (system or own) → `CategoryPermissionError` (omitting `category_id` is valid — nullable)
3. If `currency_code == user.default_currency_code`: `amount_base = amount`, `fx_rate_snapshot = Decimal("1")` (short-circuit, no DB lookup)
4. Else: `currencies.services.convert(amount, currency_code, user.default_currency_code, at=date)` → `amount_base`, `fx_rate_snapshot`
5. Atomic `Transaction.objects.create(...)`

**`update_transaction` FX rule:** Recalculate `amount_base` + `fx_rate_snapshot` only if `amount` or `currency_code` changed. Preserve snapshot otherwise.

### `apps/transactions/selectors.py`

```python
def get_transaction_list(*, user, filters) -> QuerySet[Transaction]
def get_transaction_summary(*, user, date_from, date_to, group_by) -> dict
```

**Summary uses Django `Window` + `Sum` for running balance:**
```python
Transaction.objects.filter(...).annotate(
    signed_amount=Case(
        When(type="income", then=F("amount_base")),
        default=-F("amount_base")
    )
).annotate(
    cumulative_net=Window(
        expression=Sum("signed_amount"),
        order_by=F("date").asc()
    )
)
```

---

## 5. Error Taxonomy

Added to `common/exceptions.py`:

| Exception | HTTP | Code |
|-----------|------|------|
| `CategoryNotFoundError` | 404 | `CATEGORY_NOT_FOUND` |
| `CategoryPermissionError` | 403 | `CATEGORY_PERMISSION_DENIED` |
| `CategoryCycleError` | 400 | `CATEGORY_CYCLE_DETECTED` |
| `CategoryDepthError` | 400 | `CATEGORY_MAX_DEPTH_EXCEEDED` |
| `TransactionNotFoundError` | 404 | `TRANSACTION_NOT_FOUND` |

---

## 6. Testing Strategy

**Target:** ~35-40 new tests → ~110 total, ≥94% coverage.

### Category tests
- `GET ?format=tree` returns nested structure with system + user categories merged
- `GET ?format=flat` returns flat list
- User cannot see other user's categories
- User cannot update/delete system category → 403
- User cannot update/delete another user's category → 404
- Cycle detection: A → B → C → A → `CategoryCycleError` (400)
- Max depth: 10+ levels → `CategoryDepthError` (400)
- Soft delete: linked transactions become `category=null`

### Transaction tests
- Create with same currency: `fx_rate_snapshot=1`, `amount_base=amount`
- Create with foreign currency: `amount_base` and `fx_rate_snapshot` correct
- Create with unknown currency → 400
- Update `amount` only → FX recalculated
- Update `description` only → FX snapshot preserved
- Soft delete: not in list, visible via `all_objects`
- Each filter param tested independently (type, category, currency, date range, amount range, search)
- Ordering by date and amount (asc/desc)
- Summary: `total_income`, `total_expense`, `net` arithmetic correct
- Running balance: `group_by=month` produces correct cumulative values
- Access other user's transaction → 404

### E2E flow
```
register → login → create user subcategory under system category
→ create expense transaction (USD) → verify FX snapshot stored
→ create income transaction (TRY) → verify rate=1
→ filter by category → filter by date range → search by description
→ get monthly summary → verify running balance
→ soft delete transaction → verify not in list
```

---

## 7. Out of Scope (Phase 4)

- Transfer transactions (account-to-account) — Phase 8+
- Investment transactions (stocks/crypto buy-sell) — Phase 8+
- Recurring/scheduled transactions — Phase 5
- Budget linkage — Phase 5
- Attachment uploads (receipts) — Phase 8+
- CSV/PDF export — Phase 8+
