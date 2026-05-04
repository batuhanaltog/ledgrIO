# Phase 5 — Budgets + Alerts: Design Spec

**Status:** Approved 2026-05-01  
**ADRs:** D-009, D-010, D-011, D-012

---

## Model: Budget

| Field | Type | Constraint |
|---|---|---|
| `id` | PK | auto |
| `user` | FK → User | `on_delete=CASCADE`, db_index |
| `name` | `CharField(100)` | not null |
| `category` | FK → Category | `on_delete=SET_NULL`, nullable — `null` = all categories |
| `amount` | `DecimalField(20,8)` | not null, > 0 |
| `date_from` | `DateField` | not null |
| `date_to` | `DateField` | not null |
| `alert_threshold` | `DecimalField(20,8)` | nullable — 0–1 ratio (e.g. 0.80 = 80%); `null` = no alert |
| `alert_sent_at` | `DateTimeField` | nullable — idempotency guard |
| `created_at` | `DateTimeField` | auto_now_add |
| `updated_at` | `DateTimeField` | auto_now |

**Constraints:**
- `date_to >= date_from` — DB check constraint + model `clean()`
- `alert_threshold`: `MinValueValidator(0)`, `MaxValueValidator(1)`
- Composite index: `(user, date_from, date_to)`
- Hard delete (no soft delete — budget is not financial data itself)
- `category=null` semantics: covers ALL categories (general budget use case)

---

## Endpoints

| Method | URL | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/v1/budgets/` | List budgets with `spent` annotated | JWT |
| `POST` | `/api/v1/budgets/` | Create budget | JWT |
| `GET` | `/api/v1/budgets/<pk>/` | Budget detail + spent | JWT |
| `PATCH` | `/api/v1/budgets/<pk>/` | Update budget | JWT |
| `DELETE` | `/api/v1/budgets/<pk>/` | Hard delete budget record | JWT |

**Response fields (per budget):** `id, name, category, amount, date_from, date_to, alert_threshold, alert_sent_at, spent, remaining, usage_pct`  
`spent` / `remaining` / `usage_pct` — read-only, Subquery annotated (§11)

---

## Service Signatures

```python
# services.py
def create_budget(*, user: User, data: dict) -> Budget
    # Validates date_to >= date_from
    # Validates category ownership (if provided)
    # Single row write

def update_budget(*, budget: Budget, data: dict) -> Budget
    # Same validations
    # Resets alert_sent_at if amount or alert_threshold changed

def delete_budget(*, budget: Budget) -> None
    # Hard delete

def check_and_send_budget_alerts(*, budget: Budget) -> bool
    # Returns True if alert sent
    # Guards: alert_sent_at not null → skip
    #         alert_threshold is None → skip
    #         usage_pct < threshold → skip
    # On trigger: send email + set alert_sent_at (@transaction.atomic)

# selectors.py
def get_budget_queryset(*, user: User) -> QuerySet[Budget]
    # annotate(spent=Subquery(...), remaining=..., usage_pct=...)
    # select_related("category")

def get_budget_for_user(*, user: User, pk: int) -> Budget
    # same annotation, raises NotFound if missing or wrong user
```

---

## D-012: fx_rate_override (separate commit, same phase)

`create_transaction` and `update_transaction` services gain:
```python
fx_rate_override: Decimal | None = None
```
If provided: skip `convert()`, use directly for `fx_rate_snapshot` and `amount_base`.  
If not: existing fallback + stale guard behavior unchanged.

---

## Beat Task

- **Schedule:** 07:00 UTC daily (data migration, DatabaseScheduler pattern — D-003)
- **Task:** iterate active budgets (date_from ≤ today ≤ date_to), call `check_and_send_budget_alerts()`
- **Idempotent:** `alert_sent_at` guard prevents double-send

---

## Test Strategy

### Budget endpoints (financial calc → 5 types each)
- Happy path: create → `spent=0`, `remaining=amount`
- Happy path with spend: transactions exist → `spent` correct via Subquery
- Auth guard: 401
- Ownership: 404 for another user's budget
- Validation: `date_to < date_from`, negative amount, `threshold > 1` → 400
- Edge: `category=null` → all categories included
- Edge: `usage_pct == threshold` → alert triggers (boundary)

### Alert beat (idempotency focused)
- `usage_pct < threshold` → no email, `alert_sent_at` null
- `usage_pct >= threshold` → email mocked, `alert_sent_at` set
- Idempotent: `alert_sent_at` already set → no second email
- `alert_threshold=None` → skip

### D-012 fx_rate_override
- Override provided → `fx_rate_snapshot` = override value, `amount_base` correct
- Override not provided, rate exists → normal `convert()` flow
- Override not provided, stale → `StaleFxRateError` raised

**Mock strategy:** `django.core.mail.send_mail` mocked for alert tests. Beat task tested via direct `check_and_send_budget_alerts()` call — no Celery runner mock.
