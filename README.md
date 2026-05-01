# Ledgr.io

A personal finance tracker for individuals and households. Track income and expenses across multiple accounts, manage debts with payment history, set up recurring transactions, and get monthly summaries — all with multi-currency support and FX rate snapshots.

**Design point:** personal/family scale, not multi-tenant SaaS. No RBAC, no idempotency keys, no compliance audit trails. Correctness and financial precision over scale.

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 + Celery (worker + beat) |
| Frontend | React 18 + Vite + TypeScript *(Phase 6)* |
| UI | ShadcnUI + Tailwind CSS *(Phase 6)* |
| Containerization | Docker Compose |

## Features (current)

- **Auth** — JWT (access + refresh), email verification, password reset, rate-limited login
- **Multi-currency** — currency catalog, FX rate snapshots via [Frankfurter](https://www.frankfurter.app/), daily Celery beat at 06:30 UTC, 1h Redis cache, stale-rate guard
- **Accounts** — Cash / Bank / Credit Card / Savings; computed `current_balance` (never stored); soft delete blocked while transactions exist
- **Transactions** — income/expense with FX snapshot at write time; filters by type, category, currency, date range, amount, text search; daily/weekly/monthly running balance summary
- **Categories** — unlimited hierarchy, system + user-owned, soft delete
- **Debts** — balance tracking, `expected_monthly_payment`, atomic payment flow (transaction + payment + balance decrement in one DB transaction), monthly summary vs income
- **Recurring templates** — weekly/monthly/yearly; idempotent daily materialization at 03:00 UTC; Feb-31 clamping and leap-year handling
- **Password reset** — token-based (1h TTL), always returns 200 to prevent user enumeration

## Quick Start

```bash
cp .env.example .env
# Set DJANGO_SECRET_KEY, DB credentials, Redis URL in .env

docker compose up -d --build
docker compose exec backend python manage.py migrate
```

- API root: http://localhost:8000/api/v1/
- Swagger docs: http://localhost:8000/api/v1/docs/
- Health check: http://localhost:8000/api/v1/health/
- Django admin: http://localhost:8000/admin/

## Development Commands

```bash
# Run tests with coverage report
docker compose exec backend pytest --cov=. --cov-report=term-missing

# Lint
docker compose exec backend ruff check .

# Type check
docker compose exec backend mypy .

# Create a migration
docker compose exec backend python manage.py makemigrations

# Apply migrations
docker compose exec backend python manage.py migrate

# Reset dev database (wipes all data)
docker compose down -v && docker compose up -d
```

## API Overview

```
POST   /api/v1/auth/register/
POST   /api/v1/auth/login/
POST   /api/v1/auth/refresh/
POST   /api/v1/auth/logout/
POST   /api/v1/auth/verify-email/
POST   /api/v1/auth/password-reset/
POST   /api/v1/auth/password-reset/confirm/

GET    /api/v1/users/me/
PATCH  /api/v1/users/me/

GET    /api/v1/currencies/
GET    /api/v1/fx/?base=USD&quote=TRY[&date=YYYY-MM-DD]

GET    /api/v1/accounts/
POST   /api/v1/accounts/
GET    /api/v1/accounts/summary/
GET    /api/v1/accounts/<pk>/
PATCH  /api/v1/accounts/<pk>/
DELETE /api/v1/accounts/<pk>/

GET    /api/v1/transactions/
POST   /api/v1/transactions/
GET    /api/v1/transactions/summary/
GET    /api/v1/transactions/<pk>/
PATCH  /api/v1/transactions/<pk>/
DELETE /api/v1/transactions/<pk>/

GET    /api/v1/categories/
POST   /api/v1/categories/
...

GET    /api/v1/debts/
POST   /api/v1/debts/
GET    /api/v1/debts/monthly-summary/?year=2026&month=5
GET    /api/v1/debts/<pk>/
PATCH  /api/v1/debts/<pk>/
DELETE /api/v1/debts/<pk>/
POST   /api/v1/debts/<pk>/payments/
DELETE /api/v1/debts/<pk>/payments/<ppk>/

GET    /api/v1/recurring/
POST   /api/v1/recurring/
GET    /api/v1/recurring/<pk>/
PATCH  /api/v1/recurring/<pk>/
DELETE /api/v1/recurring/<pk>/
```

## Architecture

All business logic lives in `services.py`. Read-only queries live in `selectors.py`. Views validate input and delegate — nothing more. See [`docs/ARCHITECTURE_RULES.md`](./docs/ARCHITECTURE_RULES.md) for the full ruleset and [`CLAUDE.md`](./CLAUDE.md) for the phase plan and lessons learned.

## Testing

178 tests · 83% coverage · 0 mypy errors (post Phase 4.5)

Coverage floors: services/selectors 90%, views 75%, project-wide 80% (CI-enforced).

## Roadmap

| Phase | Status |
|---|---|
| 1–3.5 Auth, currencies, hardening | ✅ Done |
| 4. Transactions + categories | ✅ Done |
| 4.5. Accounts + debts + recurring | ✅ Done |
| 5. Budgets + alerts | ⏳ Next |
| 6. Frontend skeleton + auth | ⏳ Planned |
| 7. Frontend dashboard | ⏳ Planned |
| 8+. Investments, reports, observability | — |
