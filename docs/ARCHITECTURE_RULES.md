# Ledgr.io — API & Architecture Rules

These rules supplement CLAUDE.md and are binding for all phases of development.

---

## 0. Project Scope

Ledgr.io is a **personal/family-scale** finance tracking application — income/expense, debts, recurring entries, multi-account balance, basic investment tracking, budgets and alerts.

Multi-tenant SaaS assumptions are **out of scope**:
- Idempotency keys / request deduplication
- Optimistic locking / `select_for_update`
- RBAC / sharing / per-resource ACLs
- Formal compliance (KVKK / GDPR audit trails for legal evidence)
- Court-grade audit log
- Per-endpoint rate limiting beyond auth
- Zero-downtime migration choreography

If the scope changes, this section is the first thing to revisit.

---

## 1. Single-Responsibility API Design

**Rule:** Each endpoint handles exactly one action. An API that lists resources does not also create. An API that creates does not also validate unrelated things.

**Acceptable exceptions:**
- `GET` detail + `GET` list on the same URL (standard REST)
- `PATCH` on a resource that also fetches it
- A write may produce 1-2 closely related side-effects (e.g., creating a `DebtPayment` also creates a `Transaction` and decrements `Debt.current_balance` — these are one logical operation, atomic)

**Anti-pattern:** A single `POST /api/v1/budgets/` that creates a budget, allocates sub-categories, and sends a welcome email. Split or move side-effects to background tasks.

---

## 2. Layer Contracts

```
View        → receives request, validates input via serializer, calls service or selector, returns response
Service     → owns all writes and business logic; no HTTP knowledge, no serializer imports
Selector    → owns all reads; returns QuerySet or typed dict; no writes
Model       → data + constraints only; no business methods beyond simple properties
Serializer  → shapes data in/out; no business logic, no DB queries beyond `PrimaryKeyRelatedField`
Celery task → thin wrapper; calls a service function, handles retries; no inline business logic
```

**Flexibility:** A selector smaller than ~20 lines may live inline in `services.py`. An app with no read-only logic does not need a `selectors.py` file. The `services.py` / `views.py` separation is non-negotiable; everything else is judgment.

**Violations to catch:**
- Querying the DB from a serializer `validate_*` method (use a service/selector)
- Business logic in a view beyond "validate → delegate → respond"
- Importing serializers in `services.py` (circular dep signal)

---

## 3. Mandatory Testing for Every Endpoint

**Coverage policy (tiered):**

| Layer | Floor |
|-------|-------|
| `services/` and `selectors/` | 90% |
| `views/` | 75% |
| Project-wide | 80% |

CI enforces project-wide via `--cov-fail-under=80`. Layer-specific floors are aspirational, audited manually before phase completion.

**Required tests per endpoint:**

For endpoints that touch financial calculation (FX, balance, budget usage, debt payment):
- Happy path (2xx + payload shape)
- Auth guard (401 unauthenticated)
- Ownership (404 for another user's resource)
- Validation (400 envelope on bad input)
- At least one business-rule edge case

For pure CRUD endpoints (e.g., updating a category name):
- Happy path
- Auth guard
- Ownership

Services and selectors get unit tests **independent of views**. A passing view test does not prove the service is correct.

---

## 4. Error Envelope Contract

All errors use the uniform envelope defined in `common/exceptions.py`:

```json
{
  "error": {
    "type": "VALIDATION_ERROR | NOT_FOUND | PERMISSION_DENIED | CONFLICT | RATE_LIMITED | STALE_FX_RATE | ...",
    "detail": "<human-readable or nested DRF errors>",
    "status": 400
  }
}
```

New error types go in `common/exceptions.py`, never inline. New `status → type` mappings go in `_TYPE_BY_STATUS`.

---

## 5. Financial Precision

- All monetary fields: `DecimalField(max_digits=20, decimal_places=8)`
- All Python monetary math: `decimal.Decimal`, never `float`
- **Rounding:** `ROUND_HALF_EVEN` (banker's rounding) for every quantize. Set globally in a helper, do not pass mode per call:
  ```python
  # common/money.py
  from decimal import Decimal, ROUND_HALF_EVEN
  QUANTUM_8DP = Decimal("0.00000001")
  def q(amount: Decimal, places: int = 8) -> Decimal:
      return amount.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_EVEN)
  ```
- **Single quantize at the end** of a calculation chain, never mid-chain. FX `convert()` returns raw Decimal; only the outermost service quantizes.
- **Currency-aware display precision:** `Currency.decimal_places` field (TRY/USD: 2, JPY: 0, BTC: 8). Serializers use this for output formatting; storage stays at 8dp.
- Never store a derived value that can be recalculated from stored primitives, **unless** it is an immutable historical snapshot (`fx_rate_snapshot`, `amount_base`).

---

## 6. Model Size Limits

**Soft limit:** A model with >15 fields is a smell. Audit before adding.

**Hard rule:** Models hold data and constraints only. Allowed methods:
- Simple `@property` deriving from existing fields
- `soft_delete()` / `restore()` (from base class)
- `__str__`

Business rules requiring other models, services, or queries belong in `services.py`.

---

## 7. View Size Limits

A view method should not exceed ~20 lines. If it does, business logic has leaked from the service. Refactor the service, not the view.

A view file with >4 classes likely covers too many resources. Split into a sub-module.

---

## 8. Transactional Atomicity

Any service function that mutates **two or more rows** must be wrapped in `@transaction.atomic`. Examples:
- `record_debt_payment` — writes `Transaction`, `DebtPayment`, mutates `Debt.current_balance`
- Recurring materialize — writes `Transaction`, mutates `RecurringTemplate.last_generated_date`
- Account deletion with cascade — touches multiple tables

Single-row mutations (a plain `Transaction.objects.create(...)`) do not need an explicit atomic wrapper — a single INSERT is already atomic at the DB level.

---

## 9. Celery Task Design

- One task = one service call. No multi-step orchestration inline.
- `autoretry_for=(OperationalError, requests.RequestException, ...)` with exponential backoff on tasks that touch external APIs or the DB under contention.
- Beat schedule defined in **data migrations**, not `CELERY_BEAT_SCHEDULE` (Phase 3 pattern: `apps/currencies/migrations/0003_register_daily_fx_beat.py`).
- **Idempotent:** running a task twice does not corrupt data. Use `last_generated_date` / `alert_sent_at` guards.

---

## 10. Soft Delete Contract

- `Model.objects` returns only live rows (default manager filters `deleted_at__isnull=True`).
- `Model.all_objects` returns everything — admin/audit/restore only.
- **Hard deletes are prohibited on user-owned financial data** (transactions, debts, accounts with history). Soft delete only.
  - **Exception:** `DebtPayment` is hard-deleted in reversal flows — the paired `Transaction` is soft-deleted to preserve audit trail. Hard delete is only permitted via an explicit reversal service with a corresponding ADR (see D-008). Any new hard-delete exception requires a new ADR before merge.
- `on_delete` policy:
  - User → preserve financial records: prefer `PROTECT` or soft-delete cascade; never plain `CASCADE` for financial tables
  - Account → `PROTECT` (force user to migrate transactions first; respond 409 CONFLICT)
  - Category → `SET_NULL` for transactions (preserve the row, drop the link)

---

## 11. Performance & Indexing

- Composite indexes are mandatory on user-scoped tables that filter or order by date/created_at:
  - `(user, date)` for transactions ✅
  - `(user, type)` and `(user, category)` for transactions ✅
  - `(user, account)` for transactions — **pending, tech debt**
  - `(user, created_at)` for any list endpoint that paginates by recency
- **N+1 in list endpoints is a defect, not a performance "concern".** Use one of:
  - `select_related()` for FK
  - `prefetch_related()` for reverse FK / M2M
  - `annotate(Subquery(...))` for aggregated computed fields (e.g., budget `spent`)
- Subquery pattern for per-row aggregates (Phase 5 reference):
  ```python
  spent_subquery = Transaction.objects.filter(
      user=OuterRef("user"), category=OuterRef("category"),
      date__gte=OuterRef("date_from"), date__lte=OuterRef("date_to"),
  ).values("user").annotate(total=Sum("amount_base")).values("total")

  Budget.objects.filter(user=user).annotate(
      spent=Coalesce(Subquery(spent_subquery), Decimal("0"),
                     output_field=DecimalField(max_digits=20, decimal_places=8))
  )
  ```

---

## 12. FX Freshness

`FxRate` snapshots age. Hardcoded thresholds in `apps/currencies/services.py`:

```python
FX_STALE_WARNING_DAYS = 7
FX_STALE_ERROR_DAYS   = 30
```

- Snapshot age ≤ 7 days → silent
- 7 < age ≤ 30 days → response includes `"stale_fx_warning": true` field; UI can surface a banner
- Age > 30 days → service raises `StaleFxRateError` (400, `STALE_FX_RATE`)

The Frankfurter daily beat task is the primary defense; this is the secondary guard for when beat fails or for very old historical conversions.

**Historical entry scenario:** If a user enters a transaction dated 2+ years ago and no FxRate exists for that date, `convert()` falls back to the nearest available rate. If no rate exists within 30 days of the target date, `StaleFxRateError` is raised. Resolution: user provides `fx_rate_override` in the request payload, or pre-seeds the rate via the FX endpoint. This is an **open product decision** — see D-012.

---

## 13. Budget Currency Denomination

Budgets are always denominated in the **user's base currency** (`UserProfile.default_currency_code`). Usage (`spent`) is computed from `Transaction.amount_base` (already converted to base currency at write time). Multi-currency budget support is out of scope for personal-scale design.

See D-010 and D-011 for the model decisions behind this.

---

## 15. Success Response Envelope

Decided early to avoid frontend refactor pain:

- **List endpoints** (paginated): DRF default — `{"results": [...], "count": N, "next": ..., "previous": ...}`
- **Detail / Create / Update endpoints**: bare object, no envelope. Status code conveys intent (200/201/204).
- **Aggregation / summary endpoints** (`/summary/`, `/monthly-summary/`): bare object, same as detail. Not paginated.
- **Errors** (any endpoint): always wrapped in the error envelope (Section 4).

The asymmetry between success-bare and error-wrapped is intentional — frontend has one error-handler path, success paths consume the natural shape.

---

## 16. Backup & Restore

**Postgres volume is the single point of failure for user data. Backup is mandatory infrastructure, not a feature.**

Required by end of Phase 4.5:

- `scripts/backup_postgres.sh` — daily `pg_dump` to `backups/` with 7-day rotation, runs via host cron (not Docker, to survive container loss)
- Off-site encrypted copy: rclone or `aws s3 cp` to a personal bucket (Backblaze B2 / S3 / GCS — free/cheap tier sufficient at this scale)
- `docs/runbooks/restore-from-backup.md` — step-by-step restore procedure
- **Restore drill:** the procedure must be executed end-to-end at least once on a scratch volume. Document the run.

> An untested backup is not a backup.

Schedule a quarterly restore drill once production data exists.

---

## 17. Proactive Warning Triggers

The following patterns must be flagged immediately during development:

| Pattern | Risk |
|---------|------|
| `float` in any monetary calculation | Precision loss |
| `Decimal.quantize()` without explicit `ROUND_HALF_EVEN` | Rounding bias |
| `request.user` accessed outside the view layer | Scope leak |
| `.objects.all()` without a user filter in a multi-tenant query path | Data leak |
| Two-row mutation without `@transaction.atomic` | Partial-write corruption |
| `except Exception:` or bare `except:` | Swallowed errors |
| `print()` in production code paths | Log pollution |
| FK traversal in a list view without `select_related` | N+1 |
| Per-row aggregation in a list view without `Subquery` | N+1 |
| Hardcoded currency code outside seed migrations or `Currency.code` lookups | Maintainability |
| Beat schedule added to `CELERY_BEAT_SCHEDULE` setting (vs. data migration) | Phase 3 pattern violation |
