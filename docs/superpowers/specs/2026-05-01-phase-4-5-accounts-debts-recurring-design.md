# Phase 4.5: Accounts + Debts + Recurring — Design Spec

**Date:** 2026-05-01
**Status:** Approved (plan: `~/.claude/plans/proje-mimarimi-ger-ek-bir-stateful-mist.md`)
**Scope:** Three new Django apps (`apps/accounts/`, `apps/debts/`, `apps/recurring/`) + `Transaction.account` FK + backup infrastructure + password reset endpoint.
**Why this exists:** Phase 5 (Budgets) cannot be designed correctly without knowing which account a transaction came from, whether it was a recurring entry, or whether it was a debt payment. These three apps fill structural gaps revealed during Phase 5 brainstorming.

---

## 1. Architecture Overview

```
apps/
├── categories/        (Phase 4)
├── transactions/      (Phase 4 — gets `account` FK)
├── accounts/          (NEW — multi-account balances)
├── debts/             (NEW — debt tracking + payments)
└── recurring/         (NEW — recurring transaction templates)
```

**Dependency direction (strict):**
- `accounts` depends on: `users`, `currencies`
- `debts` depends on: `users`, `currencies`, `accounts`, `transactions`
- `recurring` depends on: `users`, `currencies`, `categories`, `accounts`, `transactions`
- `transactions` is **modified** to depend on `accounts` (FK NOT NULL)

No app imports a higher-numbered app. No circular imports.

**Pattern:** Each app keeps the established layout — `models.py`, `services.py`, `selectors.py` (or inline if <20 lines), `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`, `tests/`.

---

## 2. Data Models

### 2.1 `apps/accounts/models.py`

```python
ACCOUNT_TYPE_CHOICES = [
    ("cash",        "Cash"),          # wallet, household cash
    ("bank",        "Bank"),          # checking / savings deposit
    ("credit_card", "Credit Card"),
    ("savings",     "Savings"),       # interest-bearing, ring-fenced
]


class Account(TimestampedModel, SoftDeleteModel):
    user            = ForeignKey(User, on_delete=CASCADE, related_name="accounts")
    name            = CharField(max_length=100)
    account_type    = CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    currency_code   = CharField(max_length=10)        # validated against Currency.code
    opening_balance = DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    is_active       = BooleanField(default=True)      # archive without deleting
    notes           = TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["user", "name"],
                condition=Q(deleted_at__isnull=True),
                name="account_user_name_unique_alive",
            ),
        ]
        indexes = [
            Index(fields=["user", "account_type"]),
            Index(fields=["user", "is_active"]),
        ]
```

**Notes:**
- `currency_code` is frozen once any transaction references the account. Service enforces; not a DB constraint.
- `current_balance` is **never stored** — it is computed via annotation in the selector (`opening_balance + Σ signed transactions`). Keeps the row immutable to historical activity.
- `is_active=False` accounts are hidden from default lists but visible via filter (`?include_archived=true`).

### 2.2 `apps/transactions/` modifications

Add `account` FK:

```python
class Transaction(TimestampedModel, SoftDeleteModel):
    # ... existing fields ...
    account = ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,    # cannot delete account with linked tx
        related_name="transactions",
    )
```

**Migration `apps/transactions/migrations/0002_drop_existing_and_add_account_fk.py`:**
1. `RunPython` step: delete all existing `Transaction` rows (no production data; user confirmed wipe).
2. `AddField` for `account` with `null=False` (no default needed since table is empty).
3. `AddIndex` for `(account, date)`.

### 2.3 `apps/debts/models.py`

```python
class DebtCategory(TimestampedModel, SoftDeleteModel):
    user   = ForeignKey(User, on_delete=CASCADE, related_name="debt_categories")
    name   = CharField(max_length=100)        # "Garanti Bankası", "Kişisel"
    parent = ForeignKey("self", null=True, blank=True, on_delete=PROTECT,
                        related_name="children")

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["user", "parent", "name"],
                condition=Q(deleted_at__isnull=True),
                name="debtcat_user_parent_name_unique_alive",
            ),
        ]
        indexes = [Index(fields=["user", "parent"])]


class Debt(TimestampedModel, SoftDeleteModel):
    user                     = ForeignKey(User, on_delete=CASCADE, related_name="debts")
    category                 = ForeignKey(DebtCategory, null=True, blank=True,
                                          on_delete=SET_NULL, related_name="debts")
    name                     = CharField(max_length=200)         # "Kart asgari", "Konut kredisi taksit 3"
    original_amount          = DecimalField(max_digits=20, decimal_places=8)
    current_balance          = DecimalField(max_digits=20, decimal_places=8)
    expected_monthly_payment = DecimalField(max_digits=20, decimal_places=8)
    currency_code            = CharField(max_length=10)
    interest_rate_pct        = DecimalField(max_digits=7, decimal_places=4,
                                            null=True, blank=True)
    due_day                  = SmallIntegerField(null=True, blank=True)   # 1-31
    is_settled               = BooleanField(default=False)
    notes                    = TextField(blank=True)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(original_amount__gt=0),
                            name="debt_original_amount_positive"),
            CheckConstraint(check=Q(current_balance__gte=0),
                            name="debt_current_balance_nonnegative"),
            CheckConstraint(check=Q(expected_monthly_payment__gte=0),
                            name="debt_expected_payment_nonnegative"),
            CheckConstraint(check=Q(due_day__gte=1) & Q(due_day__lte=31)
                                  | Q(due_day__isnull=True),
                            name="debt_due_day_valid"),
        ]
        indexes = [
            Index(fields=["user", "is_settled"]),
            Index(fields=["user", "category"]),
        ]


class DebtPayment(TimestampedModel):
    debt        = ForeignKey(Debt, on_delete=PROTECT, related_name="payments")
    transaction = OneToOneField("transactions.Transaction", on_delete=PROTECT,
                                related_name="debt_payment")
    amount      = DecimalField(max_digits=20, decimal_places=8)   # in debt's currency
    paid_at     = DateField(db_index=True)

    class Meta:
        indexes = [Index(fields=["debt", "paid_at"])]
```

**Notes:**
- `DebtCategory` is user-scoped (unlike `categories.Category` which has a system seed). User's own organization, max depth enforced in service (5 levels — debt categorization rarely needs more).
- `DebtPayment` lives in `apps/debts/` even though `Transaction` is in `apps/transactions/` — payment is a debt-domain concept that wraps a transaction. Direction: `debts → transactions`.
- A `Debt` may exist in a different currency than the `Account` it's paid from. Service handles FX conversion at payment time.

### 2.4 `apps/recurring/models.py`

```python
RECURRING_FREQUENCY_CHOICES = [
    ("weekly",  "Weekly"),
    ("monthly", "Monthly"),
    ("yearly",  "Yearly"),
]


class RecurringTemplate(TimestampedModel, SoftDeleteModel):
    user                = ForeignKey(User, on_delete=CASCADE, related_name="recurring_templates")
    type                = CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount              = DecimalField(max_digits=20, decimal_places=8)
    currency_code       = CharField(max_length=10)
    account             = ForeignKey("accounts.Account", on_delete=PROTECT,
                                     related_name="recurring_templates")
    category            = ForeignKey("categories.Category", null=True, blank=True,
                                     on_delete=SET_NULL,
                                     related_name="recurring_templates")
    description         = CharField(max_length=255)
    frequency           = CharField(max_length=10, choices=RECURRING_FREQUENCY_CHOICES)
    day_of_period       = SmallIntegerField()        # weekly: 1-7 (Mon-Sun), monthly: 1-31, yearly: 1-366 (DOY)
    start_date          = DateField()
    end_date            = DateField(null=True, blank=True)
    last_generated_date = DateField(null=True, blank=True)   # idempotency guard
    is_active           = BooleanField(default=True)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(amount__gt=0), name="recurring_amount_positive"),
            CheckConstraint(
                check=(
                    Q(frequency="weekly", day_of_period__gte=1, day_of_period__lte=7)
                    | Q(frequency="monthly", day_of_period__gte=1, day_of_period__lte=31)
                    | Q(frequency="yearly", day_of_period__gte=1, day_of_period__lte=366)
                ),
                name="recurring_day_of_period_valid_for_frequency",
            ),
            CheckConstraint(
                check=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="recurring_end_date_after_start",
            ),
        ]
        indexes = [
            Index(fields=["user", "is_active"]),
            Index(fields=["last_generated_date", "is_active"]),  # beat task hot path
        ]
```

**Notes:**
- `day_of_period` semantics depend on `frequency`. CHECK constraint enforces ranges. Edge case: monthly day 31 in February → service clamps to last day of month (`min(day_of_period, calendar.monthrange(year, month)[1])`).
- `last_generated_date` is the date of the last successfully materialized Transaction. Beat task uses it to compute "next due date" without re-scanning history.

---

## 3. API Endpoints (Single-Responsibility)

### 3.1 Accounts (`/api/v1/accounts/`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | List user's accounts (annotated `current_balance`) |
| `POST` | `/` | Create account |
| `GET` | `/{id}/` | Detail (annotated `current_balance`, `transaction_count`) |
| `PATCH` | `/{id}/` | Update (currency_code blocked if transactions exist → 409) |
| `DELETE` | `/{id}/` | Soft delete (409 if linked transactions exist) |
| `GET` | `/summary/` | Total assets in user's base currency (sum of all accounts, FX-converted) |

**Query params for `GET /`:**
- `?account_type=bank|cash|credit_card|savings`
- `?include_archived=true|false` (default false)
- `?currency=USD`

**Response shape (list):**
```json
{
  "results": [
    {
      "id": 1, "name": "Garanti TL", "account_type": "bank",
      "currency_code": "TRY", "opening_balance": "10000.00",
      "current_balance": "12340.50", "is_active": true,
      "transaction_count": 47
    }
  ],
  "count": 1, "next": null, "previous": null
}
```

**Response shape (`GET /summary/`):**
```json
{
  "base_currency": "TRY",
  "total_assets": "85420.00",
  "by_account_type": [
    {"account_type": "cash", "total": "2000.00"},
    {"account_type": "bank", "total": "63420.00"},
    {"account_type": "savings", "total": "20000.00"}
  ],
  "stale_fx_warning": false
}
```

### 3.2 Debts (`/api/v1/debts/`)

**Categories:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/categories/` | User's debt category tree (`?format=tree|flat`) |
| `POST` | `/categories/` | Create category |
| `PATCH` | `/categories/{id}/` | Update (cycle detection in service) |
| `DELETE` | `/categories/{id}/` | Soft delete (children → 409) |

**Debts:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | List (filters: category, currency, is_settled) |
| `POST` | `/` | Create (sets `current_balance = original_amount`) |
| `GET` | `/{id}/` | Detail with embedded recent payments |
| `PATCH` | `/{id}/` | Update (cannot directly mutate `current_balance` — only via payments) |
| `DELETE` | `/{id}/` | Soft delete (409 if payments exist; user must reverse payments first) |

**Payments (debt-scoped):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/{id}/payments/` | Record payment (atomic: Transaction + DebtPayment + balance update) |
| `DELETE` | `/{id}/payments/{payment_id}/` | Reverse payment (atomic: balance restored, Transaction soft-deleted) |

**Monthly summary:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/monthly-summary/?year=&month=` | Expected vs paid breakdown by category |

**`POST /debts/{id}/payments/` request:**
```json
{"account_id": 3, "amount": "500.00", "paid_at": "2026-05-12"}
```

**`POST /debts/{id}/payments/` response (201):**
```json
{
  "id": 12,
  "amount": "500.00",
  "paid_at": "2026-05-12",
  "transaction": {"id": 178, "amount_base": "500.00", "fx_rate_snapshot": "1"},
  "debt": {"id": 5, "current_balance": "2500.00", "is_settled": false}
}
```

**`GET /monthly-summary/?year=2026&month=5` response:**
```json
{
  "month": "2026-05",
  "expected_total": "8500.00",
  "paid_total": "5200.00",
  "remaining_total": "3300.00",
  "monthly_income": "20000.00",
  "leftover_after_expected_debts": "11500.00",
  "by_category": [
    {
      "category_id": 1, "category_name": "Garanti Bankası",
      "expected": "3000.00", "paid": "1500.00", "remaining": "1500.00",
      "debts": [
        {"id": 5, "name": "Kart asgari", "expected_monthly_payment": "1500.00",
         "paid_this_month": "1500.00", "current_balance": "2500.00"}
      ]
    }
  ]
}
```

`monthly_income` is read from `UserProfile.monthly_income` (existing field). If unset, returns `null` and `leftover_after_expected_debts` is omitted.

### 3.3 Recurring (`/api/v1/recurring/`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | List templates (filter: type, is_active, account, frequency) |
| `POST` | `/` | Create template |
| `GET` | `/{id}/` | Detail with `next_due_date` (computed) and last 5 generated transactions |
| `PATCH` | `/{id}/` | Update (changing `frequency` or `day_of_period` resets `last_generated_date` to null — re-evaluation of due) |
| `DELETE` | `/{id}/` | Soft delete (already-generated transactions remain) |
| `POST` | `/{id}/materialize-now/` | Manually trigger materialize (idempotent — does nothing if already generated for current period) |

**`GET /recurring/{id}/` response:**
```json
{
  "id": 3,
  "type": "expense",
  "amount": "12000.00",
  "currency_code": "TRY",
  "account": {"id": 1, "name": "Garanti TL"},
  "category": {"id": 14, "name": "Kira"},
  "description": "Aylık kira ödemesi",
  "frequency": "monthly",
  "day_of_period": 5,
  "start_date": "2026-01-05",
  "end_date": null,
  "is_active": true,
  "last_generated_date": "2026-04-05",
  "next_due_date": "2026-05-05",
  "recent_generated": [
    {"id": 156, "date": "2026-04-05", "amount": "12000.00"},
    {"id": 132, "date": "2026-03-05", "amount": "12000.00"}
  ]
}
```

---

## 4. Service Layer Contracts

### 4.1 `apps/accounts/services.py`

```python
def create_account(*, user, name, account_type, currency_code, opening_balance, notes) -> Account
def update_account(*, account, user, **fields) -> Account
def soft_delete_account(*, account, user) -> None
def reassign_transactions(*, source_account, target_account, user) -> int  # for migration before delete
```

**Business rules:**
- `currency_code` change blocked if `account.transactions.exists()` → `AccountCurrencyLockedError` (409 CONFLICT).
- `soft_delete_account` raises `AccountInUseError` (409) if any transaction (alive) references it.
- `name` collision within user (alive only) → 409 (DB constraint enforced).

### 4.2 `apps/accounts/selectors.py`

```python
def get_account_list_with_balance(*, user, filters) -> QuerySet[Account]
def get_account_with_balance(*, account_id, user) -> Account
def get_total_assets_summary(*, user) -> dict
```

**N+1 prevention pattern:**

```python
balance_subquery = (
    Transaction.objects.filter(account=OuterRef("pk"))
    .values("account")
    .annotate(
        net=Sum(Case(
            When(type="income",  then=F("amount")),
            When(type="expense", then=-F("amount")),
            output_field=DecimalField(max_digits=20, decimal_places=8),
        ))
    ).values("net")
)

return Account.objects.filter(user=user).annotate(
    activity_net=Coalesce(Subquery(balance_subquery), Decimal("0"),
                          output_field=DecimalField(max_digits=20, decimal_places=8)),
    current_balance=F("opening_balance") + F("activity_net"),
    transaction_count=Count("transactions", distinct=True),
)
```

**Note:** `Transaction.amount` here is in the account's currency, since `Transaction.currency_code == Account.currency_code` is enforced at write time (a transaction must match its account's currency, or be flagged as cross-currency in a future phase). Phase 4.5 enforces same-currency.

### 4.3 `apps/debts/services.py`

```python
def create_debt_category(*, user, name, parent_id) -> DebtCategory
def update_debt_category(*, category, user, **fields) -> DebtCategory  # cycle/depth checks
def soft_delete_debt_category(*, category, user) -> None  # 409 if children

def create_debt(*, user, category_id, name, original_amount, expected_monthly_payment,
                currency_code, interest_rate_pct, due_day, notes) -> Debt
def update_debt(*, debt, user, **fields) -> Debt  # current_balance NOT directly editable
def soft_delete_debt(*, debt, user) -> None  # 409 if payments exist

@transaction.atomic
def record_debt_payment(*, debt, account, amount, paid_at, user, description="") -> DebtPayment:
    """
    Atomic operation:
      1. Validate amount <= debt.current_balance (DebtBalanceUnderflowError)
      2. If account.currency != debt.currency: convert amount via FX snapshot at paid_at
      3. Create Transaction (type=expense, account, amount in account currency)
      4. Create DebtPayment linking debt + transaction (amount in debt currency)
      5. Decrement debt.current_balance; mark is_settled if zero
      6. Return DebtPayment
    """

@transaction.atomic
def reverse_debt_payment(*, payment, user) -> None:
    """
    Atomic operation:
      1. Soft-delete underlying Transaction
      2. Restore debt.current_balance += payment.amount
      3. Hard-delete DebtPayment (it's an audit trail, but reversal is a clean undo
         since transaction soft-delete preserves history)
      4. Unset is_settled if was settled
    """
```

### 4.4 `apps/debts/selectors.py`

```python
def get_debt_categories_tree(*, user) -> list[dict]
def get_debt_list(*, user, filters) -> QuerySet[Debt]
def get_debt_with_payments(*, debt_id, user) -> Debt
def get_debt_monthly_summary(*, user, year, month) -> dict
```

**`get_debt_monthly_summary` strategy (single-query pass):**

1. One query: all alive debts with annotated `paid_this_month` (`Sum` of payments where `paid_at` between month bounds), grouped by `category_id`.
2. Python aggregation: build category tree, sum expected/paid per category.
3. Income lookup: single `UserProfile.objects.get(user=user).monthly_income`.

No N+1. Total: 2 queries (debts+payments via Subquery, profile).

### 4.5 `apps/recurring/services.py`

```python
def create_recurring_template(*, user, type, amount, currency_code, account_id,
                              category_id, description, frequency, day_of_period,
                              start_date, end_date) -> RecurringTemplate
    # Enforces: currency_code == Account.currency_code (RecurringTemplateInvalidError otherwise)
    # Enforces: account.user == user
def update_recurring_template(*, template, user, **fields) -> RecurringTemplate
    # Same currency-match guard if account or currency_code changes
def soft_delete_recurring_template(*, template, user) -> None

@transaction.atomic
def materialize_template_for_date(*, template, target_date) -> Transaction | None:
    """
    Idempotent. Returns None if:
      - template.last_generated_date >= target_date
      - target_date < template.start_date or > template.end_date
      - template.is_active is False
    Else:
      - Create Transaction in template.account (currency must match account; enforced
        at template-create time, so no FX needed at materialize)
      - Update template.last_generated_date = target_date
      - Return Transaction
    """

def compute_next_due_date(*, template, after_date=None) -> date | None:
    """
    Pure function (no DB writes). Computes the next date this template should
    generate, given last_generated_date and frequency/day_of_period.
    Handles edge cases: monthly day 31 in Feb → last day of Feb.
    """
```

### 4.6 `apps/recurring/tasks.py` (new file)

```python
@shared_task(autoretry_for=(OperationalError,), retry_backoff=True, max_retries=5)
def materialize_due_recurring_transactions(target_date_iso: str | None = None) -> dict:
    """
    Beat-scheduled daily at 03:00 UTC.
    Iterates all active templates where compute_next_due_date(...) <= target_date,
    calls materialize_template_for_date for each.
    Returns {"materialized": N, "skipped": M} for observability.
    """
```

Beat schedule registered via `apps/recurring/migrations/0002_register_recurring_beat.py` (DatabaseScheduler pattern, depends on `django_celery_beat` latest migration + `apps/recurring/0001_initial`).

---

## 5. Error Taxonomy (additions to `common/exceptions.py`)

| Exception | HTTP | `error.type` |
|-----------|------|--------------|
| `AccountNotFoundError` | 404 | `NOT_FOUND` |
| `AccountInUseError` | 409 | `CONFLICT` |
| `AccountCurrencyLockedError` | 409 | `CONFLICT` |
| `DebtNotFoundError` | 404 | `NOT_FOUND` |
| `DebtBalanceUnderflowError` | 400 | `VALIDATION_ERROR` |
| `DebtCategoryHasChildrenError` | 409 | `CONFLICT` |
| `DebtCategoryCycleError` | 400 | `VALIDATION_ERROR` |
| `RecurringTemplateInvalidError` | 400 | `VALIDATION_ERROR` |
| `StaleFxRateError` | 400 | `VALIDATION_ERROR` (or new `STALE_FX_RATE`) |

`_TYPE_BY_STATUS` already covers 400/404/409. `STALE_FX_RATE` is a special `error.type` value layered on top of 400 — handled by overriding the response in the service catching code, since DRF's `_TYPE_BY_STATUS` works on status code alone.

---

## 6. Migrations Order

1. `apps/accounts/0001_initial.py` — `Account` model
2. `apps/transactions/0002_drop_existing_and_add_account_fk.py` — wipe + FK NOT NULL
3. `apps/debts/0001_initial.py` — `DebtCategory`, `Debt`, `DebtPayment`
4. `apps/recurring/0001_initial.py` — `RecurringTemplate`
5. `apps/recurring/0002_register_recurring_beat.py` — beat schedule (depends on `django_celery_beat` latest)
6. `apps/currencies/0004_add_decimal_places.py` — `Currency.decimal_places` field + data migration to set TRY/USD/EUR/GBP=2, JPY=0, BTC/ETH=8

Migration #6 is independent and can run before any Phase 4.5 model migration — order it earliest in commit history so currency-aware quantize is available when Account opening_balance serializers go live.

---

## 7. Testing Strategy

**Coverage targets** (per Section 3 of `docs/ARCHITECTURE_RULES.md`):
- services/selectors: 90% per app
- views: 75%
- project-wide CI floor: 80%

**`apps/accounts/tests/`** (~12-15 tests):
- Model: name uniqueness within user, currency code validation (against `Currency`)
- Services: create, update (currency_code lock once tx exists), soft delete (409 with linked tx), reassign_transactions
- Selectors: `current_balance` annotation correctness across mixed income/expense/zero-activity
- Views: full CRUD happy path + auth + ownership + `?include_archived` + `/summary/` arithmetic + multi-currency summary FX

**`apps/debts/tests/`** (~22-26 tests):
- Model: debt amount non-negative, due_day range, category tree uniqueness
- Services:
  - `create_debt_category` cycle / depth / parent ownership
  - `record_debt_payment` happy path, balance underflow, settle on zero, cross-currency FX (USD debt, TRY account)
  - `reverse_debt_payment` restores balance, undoes settled flag
  - Atomicity: simulate FX failure mid-operation, verify rollback (use `transaction.atomic` rollback test)
- Selectors:
  - `get_debt_monthly_summary` arithmetic (expected vs paid), category breakdown, leftover_after_expected_debts with/without monthly_income
  - Single-query verification (assertNumQueries)
- Views: CRUD + payments + reverse payment + monthly-summary + ownership

**`apps/recurring/tests/`** (~14-16 tests):
- Model: day_of_period range per frequency, end_date >= start_date
- Services:
  - `compute_next_due_date` for monthly day 31 in Feb (clamp), weekly cycles, yearly DOY, end_date past
  - `materialize_template_for_date` idempotency: calling twice yields one Transaction
  - Skips inactive, expired, or already-generated templates
- Tasks: `materialize_due_recurring_transactions` happy path, retry on `OperationalError`
- Views: CRUD + manual `materialize-now` idempotency

**E2E flow** (`apps/recurring/tests/test_e2e.py` or `tests/test_phase4_5_e2e.py`):
```
register → set monthly_income on profile → create 2 accounts (cash + bank, TRY)
→ create recurring template: salary income (monthly, day=1, account=bank)
→ create recurring template: rent expense (monthly, day=5, account=bank)
→ trigger materialize for May 1 + May 5 → verify two transactions
→ create DebtCategory "Garanti", create Debt under it
→ POST /debts/{id}/payments/ → verify atomic write (Transaction + DebtPayment + balance)
→ GET /debts/monthly-summary/ → verify breakdown + leftover_after_expected_debts
→ DELETE payment → verify balance restored
→ GET /accounts/summary/ → verify total_assets reflects all activity
→ DELETE account with linked tx → 409 CONFLICT
```

---

## 8. Backup Infrastructure (deliverable at end of Phase 4.5)

**`scripts/backup_postgres.sh`:**
```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-${HOME}/ledgrio-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP_FILE="${BACKUP_DIR}/ledgrio-${TIMESTAMP}.sql.gz"
mkdir -p "${BACKUP_DIR}"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-ledgrio}" "${POSTGRES_DB:-ledgrio}" | gzip > "${DUMP_FILE}"
find "${BACKUP_DIR}" -name 'ledgrio-*.sql.gz' -mtime +${RETENTION_DAYS} -delete
# Off-site step (optional, env-gated):
# [[ -n "${BACKUP_RCLONE_REMOTE:-}" ]] && rclone copy "${DUMP_FILE}" "${BACKUP_RCLONE_REMOTE}/ledgrio/"
```

**`docs/runbooks/restore-from-backup.md`** — step-by-step:
1. Stop the stack: `docker compose down`
2. Wipe volume: `docker volume rm ledgrio_pgdata`
3. Start postgres alone: `docker compose up -d postgres`
4. Wait for ready: `docker compose exec postgres pg_isready ...`
5. Restore: `gunzip -c <backup>.sql.gz | docker compose exec -T postgres psql -U ledgrio ledgrio`
6. Start the rest: `docker compose up -d`
7. Smoke test: `curl localhost:8000/api/v1/health/`

**Drill requirement:** Procedure must be executed at least once on a scratch volume; document the run in `docs/runbooks/restore-drill-log.md` with date and result.

---

## 9. Password Reset (deliverable at end of Phase 4.5)

Adds a sibling `PasswordResetToken` model in `apps/users/models.py` (mirrors `EmailVerificationToken` shape: `token`, `user`, `expires_at`, `used_at`). Reset token TTL: **1 hour** (vs verification's 24h) — short window because the impact of a leaked reset token is account takeover, not just verification spoofing. Sharing one model with a `purpose` enum was considered and rejected: token TTLs and use-once semantics differ enough that two narrow models read more clearly than one wide one.

**Endpoints:**
- `POST /api/v1/auth/password-reset/request/` — `{email}` → 200 (always, even if email not found, to prevent enumeration)
- `POST /api/v1/auth/password-reset/confirm/` — `{token, new_password}` → 200 + invalidates all refresh tokens

Mail goes to console in dev (existing setup); production switches to Mailgun via `EMAIL_BACKEND`.

---

## 10. Out of Scope (Phase 4.5)

- Cross-currency transactions where `Transaction.currency_code != Account.currency_code` — Phase 8+. Phase 4.5 enforces same-currency at the service layer.
- Account transfer (account A → account B in one op) — Phase 8+.
- Debt amortization schedule (interest accrual over time, balance projection) — Phase 8+. `interest_rate_pct` is stored but not yet used in any calculation.
- Debt payment scheduling / autopay — Phase 8+.
- Recurring template "skip this occurrence" / "edit single instance" — Phase 8+. For now, materialize is all-or-nothing per period.
- CSV/JSON data export — Phase 8+.
- Light change history (`*_history` tables / `django-simple-history`) — Phase 8+. Not blocking.
- Reconciliation (monthly close, balance-vs-activity sanity check) — Phase 8+.

---

## 11. Risks & Solo-Dev Notes

- **Account FK migration breaks Phase 4 tests.** `factories.py` in `transactions` and `categories` need an `AccountFactory` injected. Skipping this lands "green CI, red local" until factories updated.
- **Debt FX edge case.** USD debt paid from TRY account. Service must use `apps.currencies.services.get_exchange_rate(USD, TRY, at=paid_at)`, then store both: `Transaction.amount` in account currency (TRY), `DebtPayment.amount` in debt currency (USD), `Debt.current_balance` decremented by the USD amount. Test: USD debt of $100, payment of 3300 TRY at rate 33 → debt balance drops by $100, not $3300.
- **Recurring beat conflict.** Existing FX beat at 06:30 UTC; recurring beat at 03:00 UTC — schedule names must be unique (`apps.recurring.tasks.materialize_due_recurring_transactions`).
- **`monthly_income` as the source of truth for "leftover" calc.** If user has unsteady income (freelance), this single number lies. Future phase may compute trailing-12-month average from income transactions. For now, document as a hint.
- **Polymorphic debt regret.** If user later asks for credit-card-specific fields (statement_day, minimum_payment_pct) or installment-specific fields (installment_count, current_installment), we extend `Debt` with nullable fields rather than introducing subclasses. Add a `metadata` JSONField only if 3+ such fields accumulate.
- **DebtPayment hard-delete on reverse.** We chose hard-delete on reversal (with the underlying Transaction soft-deleted). This means reversal history is lost. If audit becomes important, switch DebtPayment to soft-delete + add `reversed_at` field. For personal use, fine.
- **Backup is a feature, not infra.** Treat the script + runbook as Phase 4.5 acceptance criteria. Phase done = backup tested.
