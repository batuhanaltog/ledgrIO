# Ledgr.io — Claude Code Project Guide

## 🚀 Project Overview
Ledgr.io is a high-level Fintech SaaS platform for budget and portfolio management (Stocks, Crypto, Personal Expenses).

**Tech Stack:** Django 5 (DRF) · React 18 (Vite + TypeScript) · PostgreSQL 16 · Redis 7 · Celery · Docker.
**Key Focus:** Financial precision (Decimal), scalability, rigorous testing.

## 🛠 Build & Run Commands
- Stack: `docker-compose up -d --build`
- Backend test + cov: `docker-compose exec backend pytest --cov=. --cov-report=term-missing`
- Frontend dev: `cd frontend && npm run dev`
- Migrations: `docker-compose exec backend python manage.py migrate`
- Lint (Python): `docker-compose exec backend ruff check .`
- Type check: `docker-compose exec backend mypy .`

**Endpoints (live):**
- Health: http://localhost:8000/api/v1/health/
- Swagger: http://localhost:8000/api/v1/docs/
- Admin: http://localhost:8000/admin/

## 🏗 Architectural Rules (Strict)
- **Service Pattern:** All business logic MUST reside in `services.py`. Models hold data; views handle request/response only. Read queries go in `selectors.py`.
- **Financial Precision:** Never use `Float` for currency. Always `DecimalField(max_digits=20, decimal_places=8)` and Python `decimal.Decimal`.
- **Type Hinting:** Mandatory for all Python functions and TS components. Use `Final`, `Literal`, `TypedDict` where applicable.
- **API Design:** RESTful + versioned under `/api/v1/`. Every endpoint documented via drf-spectacular OpenAPI.
- **Frontend:** React functional components + TanStack Query. ShadcnUI for primitives, Tailwind for styling. Avoid generic AI-styled UI — aim for distinctive, professional design.

## 🧪 Testing Standards
- Target: minimum **90% test coverage** (current: **91%** after Phase 1).
- Backend: `pytest` + `factory-boy`. Focus on edge cases in financial logic.
- Frontend: Vitest unit tests; E2E for critical flows.

## 📝 Code Style
- Backend: PEP 8, ruff lint, methods descriptive (`calculate_portfolio_weighted_return`, not `calc_return`).
- Frontend: Tailwind CSS, prefer `interface` over `type` for object shapes in TS.
- Git: atomic commits with prefix (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).

## 📊 Monitoring & DevOps
- CI/CD: Jenkins pipeline (planned).
- Observability: Grafana + Prometheus exporter (Phase 8).
- Error tracking: Sentry (wired in `config/settings/production.py`, requires `SENTRY_DSN`).

---

## 📦 Repo Layout

```
ledgrIO/
├── docker-compose.yml + docker-compose.override.yml   # tek paylaşılan image: ledgrio-backend:latest
├── .env.example
├── nginx/nginx.conf
├── backend/
│   ├── Dockerfile, manage.py, pytest.ini, .coveragerc, pyproject.toml
│   ├── requirements/{base,development,production}.txt
│   ├── config/{__init__.py, settings/{base,development,production}.py, urls.py, wsgi.py, asgi.py}
│   ├── celery_app/{__init__.py, celery.py, tasks/...}
│   ├── common/                  # shared abstract models, health, exceptions
│   └── apps/                    # users, currencies, transactions, budgets (eklenecek)
└── frontend/                    # eklenecek
```

**Çoklu servis tek image:** `backend`, `celery_worker`, `celery_beat` aynı `ledgrio-backend:latest` image'ini kullanır. Bağımlılık değişikliklerinde `docker compose build backend` yeterlidir; ayrı build gerekmez.

---

## 🗺️ Faz Planı

| Faz | Durum | Açıklama |
|---|---|---|
| **1. Repo iskelet + Docker** | ✅ Tamamlandı | `docker compose up` ile postgres/redis/backend/celery worker+beat çalışır. Health endpoint `database` + `redis` ok döner. |
| **2. Auth/Users (JWT)** | ✅ **Tamamlandı** | Email-based custom User + UserProfile (auto via signal). Endpoints: `/auth/register/`, `/auth/login/`, `/auth/refresh/`, `/auth/logout/` (blacklist), `/users/me/` (GET + PATCH). 27 test, %91 cov. TDD: red → green → refactor. |
| 3. Currencies + FX | ⏳ Pending | Currency, FxRate, daily Celery beat fetch, Redis-cached `convert()` |
| 4. Transactions + Categories | ⏳ Pending | Multi-currency snapshot, hiyerarşik kategori, window function summary |
| 5. Budgets + Alerts | ⏳ Pending | Budget snapshots, threshold alerts, Celery beat |
| 6. Frontend skeleton + Auth | ⏳ Pending | Vite/React/TS, Tailwind, ShadcnUI, profesyonel tasarım |
| 7. Frontend transactions + dashboard | ⏳ Pending | RHF + Zod formlar, TanStack Query, kategori grafiği |
| 8+ (sonraki) | — | Assets/Portfolios → Reports/Export → Notifications → Observability |

---

## ⚠️ Solo-Dev Tuzakları (öğrenilenler)

- **Multi-service docker-compose:** Aynı kod tabanını 3 servisten kullanırken her servise ayrı `build:` koyma — bir image build edip `image:` ile referansla. Yoksa stale image bug'ı (örn. `ModuleNotFoundError: environ`) yaşarsın.
- **Health endpoint başlangıçtan itibaren:** Container healthcheck için zorunlu; ayrıca smoke test'in tek satırlık karşılığı.
- **Celery deprecation:** `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True` set et, yoksa Celery 6.0'a kadar warning üretir.
- **Custom User model timing:** `AUTH_USER_MODEL`'i mutlaka **ilk migrate'ten önce** set et. Sonradan eklersen `InconsistentMigrationHistory` çıkar — dev'de fix: `docker compose down -v` (volume'ü siler).
- **Phase boundary trade-off:** `User.default_currency_code` şu an `CharField(3)` + regex validator. Phase 2'de `Currency` modeli geldiğinde data migration ile FK'ya promote edilecek (`apps/users/migrations/000X_currency_fk.py`).
- **simplejwt + custom User:** `TokenObtainPairSerializer.username_field = User.USERNAME_FIELD` set etmek `email` ile login için yeterli — ekstra view yazma.
