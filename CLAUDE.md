# Ledgr.io — Claude Code Project Guide

## 🚀 Project Overview
Ledgr.io is a **personal/family-scale** finance tracker — income/expense, debts, recurring entries, multi-account balance, basic investments, budgets and alerts. Single-user (or a household of a few) is the design point. Multi-tenant SaaS assumptions are explicitly out of scope (see `docs/ARCHITECTURE_RULES.md` §0).

**Tech Stack:** Django 5 (DRF) · React 18 (Vite + TypeScript) · PostgreSQL 16 · Redis 7 · Celery · Docker.
**Key Focus:** Financial precision (Decimal), correctness over scale, disciplined testing.

## 🛠 Build & Run Commands
- Stack: `docker compose up -d --build`
- Backend test + cov: `docker compose exec backend pytest --cov=. --cov-report=term-missing`
- Frontend dev: `cd frontend && npm run dev` (Phase 6+)
- Migrations: `docker compose exec backend python manage.py migrate`
- Lint: `docker compose exec backend ruff check .`
- Type check: `docker compose exec backend mypy .`
- Reset dev DB: `docker compose down -v; docker compose up -d`

**Endpoints (live):**
- Health: http://localhost:8000/api/v1/health/
- Swagger: http://localhost:8000/api/v1/docs/
- Admin: http://localhost:8000/admin/
- Auth: `POST /api/v1/auth/{register,login,refresh,logout,verify-email,password-reset,password-reset/confirm}/`
- Users: `GET/PATCH /api/v1/users/me/`
- Currencies: `GET /api/v1/currencies/`, `GET /api/v1/fx/?base=X&quote=Y[&date=Z]`
- Accounts: `GET/POST /api/v1/accounts/`, `GET/PATCH/DELETE /api/v1/accounts/<pk>/`, `GET /api/v1/accounts/summary/`
- Transactions: `GET/POST /api/v1/transactions/`, `GET/PATCH/DELETE /api/v1/transactions/<pk>/`, `GET /api/v1/transactions/summary/`
- Debts: `GET/POST /api/v1/debts/categories/`, `PATCH/DELETE /api/v1/debts/categories/<pk>/`, `GET/POST /api/v1/debts/`, `GET/PATCH/DELETE /api/v1/debts/<pk>/`, `POST /api/v1/debts/<pk>/payments/`, `DELETE /api/v1/debts/<pk>/payments/<ppk>/`, `GET /api/v1/debts/monthly-summary/`
- Recurring: `GET/POST /api/v1/recurring/`, `GET/PATCH/DELETE /api/v1/recurring/<pk>/`

## 🏗 Architectural Rules (Strict)
**Full ruleset:** `docs/ARCHITECTURE_RULES.md` is the source of truth. The summary below is a reminder, not a substitute.

- **Service Pattern:** Business logic in `services.py`; models hold data; views handle request/response only; reads via `selectors.py` (or inline if <20 lines).
- **Single-Responsibility APIs:** One endpoint, one action. List does not create. Create does not orchestrate emails.
- **Financial Precision:** `DecimalField(20,8)`, `decimal.Decimal`, `ROUND_HALF_EVEN` always. Single quantize at chain end. Currency-aware display precision via `Currency.decimal_places`.
- **Atomicity:** Any service mutating ≥2 rows uses `@transaction.atomic` (debt payment, recurring materialize, multi-step writes).
- **No N+1:** List endpoints use `select_related` / `prefetch_related` / `Subquery` annotations. Per-row aggregation in a list = bug.
- **FX Freshness:** 7+ days → warning flag; 30+ days → `StaleFxRateError`.
- **Response Shape:** List = DRF paginated dict; Detail/Create/Update = bare object; Errors = uniform envelope (`common/exceptions.py`).
- **Type Hinting:** Mandatory. `Final`, `Literal`, `TypedDict` where applicable.
- **API Versioning:** `/api/v1/`, every endpoint documented via drf-spectacular.
- **Frontend (Phase 6+):** React functional components + TanStack Query. ShadcnUI primitives, Tailwind. Avoid generic AI-styled UI.

## 🧪 Testing Standards (Tiered Coverage)
- **services / selectors:** 90% floor (audited per phase, not CI-enforced)
- **views:** 75% floor
- **Project-wide:** 80% floor — CI enforces via `pytest --cov-fail-under=80`
- Per-endpoint requirement: financial-calc endpoints get 5 test types (happy, auth, ownership, validation, edge); pure CRUD gets 3 (happy, auth, ownership).
- Current: 178 tests, ~83% coverage post-Phase-4.5.
- mypy strict-ish (`disallow_any_generics=false`); celery/environ/sentry/django_ratelimit ignored via overrides.
- Backend: `pytest` + `factory-boy`. Frontend: Vitest + E2E for critical flows.

## 🛟 Backup (Required after Phase 4.5)
Postgres volume is the single failure point.
- `scripts/backup_postgres.sh` — daily `pg_dump` + 7-day rotation via host cron
- Off-site encrypted copy (rclone / S3 / Backblaze)
- `docs/runbooks/restore-from-backup.md` — must be executed at least once. **An untested backup is not a backup.**

## 📝 Code Style
- Backend: PEP 8, ruff lint, methods descriptive (`calculate_portfolio_weighted_return`, not `calc_return`).
- Frontend: Tailwind CSS, prefer `interface` over `type` for object shapes in TS.
- Git: atomic commits with prefix (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).

## 📊 Monitoring & DevOps
- CI/CD: GitHub Actions (`.github/workflows/ci.yml`) — runs on every push/PR, enforces 80% coverage floor.
- Observability: Grafana + Prometheus exporter (Phase 8).
- Error tracking: Sentry (wired in `config/settings/production.py`, requires `SENTRY_DSN`).

---

## 📦 Repo Layout

```
ledgrIO/
├── docker-compose.yml + docker-compose.override.yml   # shared image: ledgrio-backend:latest
├── .env.example
├── nginx/nginx.conf
├── backend/
│   ├── Dockerfile, manage.py, pytest.ini, .coveragerc, pyproject.toml
│   ├── requirements/{base,development,production}.txt
│   ├── config/{__init__.py, settings/{base,development,production}.py, urls.py, wsgi.py, asgi.py}
│   ├── celery_app/{__init__.py, celery.py, tasks/...}
│   ├── common/                  # shared abstract models, health, exceptions, money helpers
│   └── apps/                    # users, currencies, categories, transactions, accounts, debts, recurring, budgets (5)
├── docs/                        # ARCHITECTURE_RULES.md, runbooks/, superpowers/specs/
├── scripts/                     # backup_postgres.sh
└── frontend/                    # coming Phase 6
```

**Multi-service single image:** `backend`, `celery_worker`, `celery_beat` all use `ledgrio-backend:latest`. On dependency changes, `docker compose build backend` is enough.

---

## 🗺️ Phase Plan

| Phase | Status | Description |
|---|---|---|
| **1. Repo skeleton + Docker** | ✅ Done | `docker compose up` — postgres/redis/backend/celery worker+beat running. Health endpoint returns `database` + `redis` ok. |
| **2. Auth/Users (JWT)** | ✅ Done | Email-based custom User + UserProfile (auto via signal). Endpoints: `/auth/register/`, `/auth/login/`, `/auth/refresh/`, `/auth/logout/` (blacklist), `/users/me/` (GET + PATCH). 27 tests, 91% cov. |
| **3. Currencies + FX** | ✅ Done | `Currency` catalog (TRY/USD/EUR/GBP/JPY/BTC/ETH seed), `FxRate` snapshot. Frankfurter.dev provider, `convert()` with fallback + 1h Redis cache. Celery beat daily 06:30 UTC. |
| **3.5. Hardening** | ✅ Done | SECRET_KEY fail-fast · SoftDeleteManager · django-ratelimit (429 envelope) · unified error taxonomy · FX single-quantize · email verification scaffold · mypy clean · GitHub Actions CI. 72 tests, 94% cov. |
| **4. Transactions + Categories** | ✅ Done | `apps/categories/` (hierarchy, soft delete) + `apps/transactions/` (FX snapshot at write, filters, summary). ~45 new tests, 93% coverage. |
| **4.5. Accounts + Debts + Recurring** | ✅ Done | `apps/accounts/` (current_balance via Subquery, currency locked once used) + `apps/debts/` (atomic payment flow, monthly summary vs income) + `apps/recurring/` (idempotent daily beat at 03:00 UTC) + password reset + backup infra. 178 tests, 83% cov. |
| 5. Budgets + Alerts | ⏳ Pending | Category-based, base-currency, `date_from`/`date_to` model. Live `usage` via Subquery. Celery beat email alert, idempotent via `alert_sent_at`. |
| 6. Frontend skeleton + Auth | ⏳ Pending | Vite/React/TS, Tailwind, ShadcnUI |
| 7. Frontend transactions + dashboard | ⏳ Pending | RHF + Zod forms, TanStack Query, category chart |
| 8+ | — | Investments/Portfolios → Reports/Export → Notifications → Observability |

---

## ⚠️ Lessons Learned (Solo-Dev)

- **Multi-service docker-compose:** Share one image across services with `image:` reference, not separate `build:` blocks per service. Avoids stale-image bugs (`ModuleNotFoundError: environ`).
- **Health endpoint from day one:** Container healthcheck + smoke test in one line.
- **Celery deprecation:** Set `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True`.
- **Custom User model timing:** Set `AUTH_USER_MODEL` before first migrate. Fix in dev: `docker compose down -v`.
- **simplejwt + custom User:** `TokenObtainPairSerializer.username_field = User.USERNAME_FIELD` is enough for email login.
- **CursorPagination + custom field:** Use `PageNumberPagination` for small enumerable tables to avoid `FieldError: Cannot resolve keyword 'created'`.
- **Celery beat + DatabaseScheduler:** `CELERY_BEAT_SCHEDULE` is ignored. Register tasks via data migration (see `apps/currencies/migrations/0003_register_daily_fx_beat.py`).
- **FX strategy:** Snapshot at write time — `fx_rate_snapshot` stored immutably. Quantize only at the outermost layer, never mid-chain.
- **JWT logout semantics:** `/auth/logout/` blacklists only the refresh token. Access token lives until TTL (15 min). Frontend must discard access token immediately.
- **Email normalization:** Override `normalize_email` to lowercase both local and domain parts. Otherwise case-sensitive lookup causes 401 on login.
- **django-ratelimit + DRF 429:** `Ratelimited` is a `PermissionDenied` subclass; DRF renders it as 403 by default. Override `drf_exception_handler` to intercept and return 429.
- **mypy + Django:** Use `disallow_any_generics=false` and `[[tool.mypy.overrides]]` to ignore untyped third-party packages (celery, environ, sentry, django_ratelimit).
- **SoftDeleteModel contract:** `Model.objects` filters deleted rows. `Model.all_objects` for admin/audit. Set `base_manager_name = "all_objects"` for FK reverse lookups.
- **Historical models in migrations:** `apps.get_model()` returns a historical model with no custom managers. Use `.objects.all()`, never `.all_objects`.
- **Transaction.account FK migration:** Wipe test-only data in the migration before adding NOT NULL FK. No data migration complexity needed when there's no production data.
- **factory-boy SelfAttribute:** Use `factory.SelfAttribute("..user")` to propagate user FK through nested SubFactory chains.
- **UnorderedObjectListWarning:** Every list view must have an explicit `.order_by()` call — no implicit ordering for pagination.
- **Coverage tiered:** services/selectors 90%, views 75%, project 80% floor. CI enforces 80% (`--cov-fail-under=80`). Layer floors are manual audit at phase end.
- **Rounding standard:** `ROUND_HALF_EVEN` everywhere. `common/money.py:q()` is the single entry point. PRs without it are rejected.
- **Backup:** Postgres volume is the single failure point. `pg_dump` cron + off-site copy + restore drill mandatory. Phase 4.5 deliverable complete.
