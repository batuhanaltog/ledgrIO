# Ledgr.io — Claude Code Project Guide

## 🚀 Project Overview
Ledgr.io is a high-level Fintech SaaS platform for budget and portfolio management (Stocks, Crypto, Personal Expenses).

**Tech Stack:** Django 5 (DRF) · React 18 (Vite + TypeScript) · PostgreSQL 16 · Redis 7 · Celery · Docker.
**Key Focus:** Financial precision (Decimal), scalability, rigorous testing.

## 🛠 Build & Run Commands
- Stack: `docker compose up -d --build`
- Backend test + cov: `docker compose exec backend pytest --cov=. --cov-report=term-missing`
- Frontend dev: `cd frontend && npm run dev` (Faz 6'da gelecek)
- Migrations: `docker compose exec backend python manage.py migrate`
- Lint: `docker compose exec backend ruff check .`
- Type check: `docker compose exec backend mypy .`
- Reset dev DB (Adım 4 öncesi sık lazım olur): `docker compose down -v; docker compose up -d`

**Endpoints (live):**
- Health: http://localhost:8000/api/v1/health/
- Swagger: http://localhost:8000/api/v1/docs/
- Admin: http://localhost:8000/admin/
- Auth: `POST /api/v1/auth/{register,login,refresh,logout,verify-email}/`
- Users: `GET/PATCH /api/v1/users/me/`
- Currencies: `GET /api/v1/currencies/`, `GET /api/v1/fx/?base=X&quote=Y[&date=Z]`

## 🏗 Architectural Rules (Strict)
- **Service Pattern:** All business logic MUST reside in `services.py`. Models hold data; views handle request/response only. Read queries go in `selectors.py`.
- **Financial Precision:** Never use `Float` for currency. Always `DecimalField(max_digits=20, decimal_places=8)` and Python `decimal.Decimal`.
- **Type Hinting:** Mandatory for all Python functions and TS components. Use `Final`, `Literal`, `TypedDict` where applicable.
- **API Design:** RESTful + versioned under `/api/v1/`. Every endpoint documented via drf-spectacular OpenAPI.
- **Frontend:** React functional components + TanStack Query. ShadcnUI for primitives, Tailwind for styling. Avoid generic AI-styled UI — aim for distinctive, professional design.

## 🧪 Testing Standards
- Target: minimum **90% test coverage** (current: **94%**, 72 tests).
- CI: GitHub Actions runs ruff + mypy + pytest --cov-fail-under=90 on every push/PR.
- mypy: strict-ish (`disallow_any_generics=false` for Django ORM realism); third-party untyped libs (celery/environ/sentry/django_ratelimit) ignored via overrides.
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
| **2. Auth/Users (JWT)** | ✅ Tamamlandı | Email-based custom User + UserProfile (auto via signal). Endpoints: `/auth/register/`, `/auth/login/`, `/auth/refresh/`, `/auth/logout/` (blacklist), `/users/me/` (GET + PATCH). 27 test, %91 cov. TDD: red → green → refactor. |
| **3. Currencies + FX** | ✅ Tamamlandı | `Currency` katalog (TRY/USD/EUR/GBP/JPY/BTC/ETH seed), `FxRate` snapshot (unique base+quote+date, check constraint base≠quote). Frankfurter.dev provider (key gerekmez), `convert()` direct + inverse + tarih fallback + 1h Redis cache. Celery beat günlük 06:30 UTC. Endpoints: `/currencies/`, `/fx/?base=X&quote=Y[&date=Z]`. |
| **3.5. Hardening (Review)** | ✅ **Tamamlandı** | Audit-driven remediation: SECRET_KEY fail-fast · SoftDeleteManager default-filters + `all_objects` · profile field allowlist · django-ratelimit (login 10/m, register 5/h) → 429 envelope · password validator unified at 10 char · health/exception types narrowed · uniform error taxonomy · FX single-quantize at end · Frankfurter `autoretry_for` + stale-snapshot guard · case-insensitive email login fix · auth flow E2E test + JWT claim assertions · FxRate orphan guard via `UnknownCurrencyError` · mypy clean (44→0) · GitHub Actions CI · email verification scaffold (`is_email_verified` + token model + `/auth/verify-email/`, mail to console). 22 yeni test, 72 toplam, %94 cov. |
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
- **CursorPagination + custom field:** Default DRF `CursorPagination` `created` field bekler. Currency gibi enumerable küçük tablolarda view-specific `PageNumberPagination` aç, yoksa `FieldError: Cannot resolve keyword 'created'`.
- **`python -c` + Django ORM:** Container içinde Django setup'ı çalışmaz. Daima `python manage.py shell -c "..."` kullan, yoksa `AppRegistryNotReady`.
- **Celery beat schedule:** `DatabaseScheduler` kullanılınca `CELERY_BEAT_SCHEDULE` setting okunmaz. Periodic task'leri data migration ile DB'ye yaz (örn. `apps/currencies/migrations/0003_register_daily_fx_beat.py`). Migration dependency olarak `django_celery_beat`'in en son migration'ını yaz, yoksa "node not in graph" hatası alırsın.
- **FX strategy:** Snapshot pattern — `FxRate` rate'i kayıt anında store edilir, eski transaction'lar değişmez. `convert()` direct rate yoksa inverse'i 1/rate ile dener; ikisi de yoksa o tarihten önceki en yakın rate'e fallback yapar. **Quantize sadece sonda** (`amount * raw_rate` sonrası tek 8dp), `_lookup_rate` ham Decimal döner — yoksa inverse path'te compounding rounding olur.
- **JWT logout semantik:** `/auth/logout/` sadece **refresh token**'ı blacklistler. Access token TTL'i (15 dk) dolana kadar çalışır. Stateless JWT'nin tasarım gereği. Server-side per-request revocation list = JWT'nin değerini sıfırlar = istemiyoruz. Frontend bu yüzden access'i hemen düşürmeli.
- **Email normalization:** `UserManager.normalize_email` Django'nun default'unu **override eder**, hem local-part hem domain lowercase olur (Bob@LEDGR.IO → bob@ledgr.io). Aksi takdirde case-sensitive `EmailField` lookup yüzünden login 401 atar. Test: `test_login_with_uppercase_email_works`.
- **django-ratelimit + DRF 429:** `Ratelimited` exception `PermissionDenied` subclass'ı, DRF default 403 render eder. `common/exceptions.drf_exception_handler` Ratelimited'i intercept edip 429 + `RATE_LIMITED` envelope döndürür.
- **mypy + Django realism:** `strict=true` Django ORM generics'ine karşı çok loud. `disallow_any_generics=false` aç, üçüncü-parti stub'sız paketleri (celery, environ, sentry_sdk, django_ratelimit) `[[tool.mypy.overrides]]` ile ignore et. Sonrası temiz yönetilebilir.
- **django-stubs model resolution:** Custom model'lar `models.py`'da olmalı, başka modülde tanımlanırsa `.objects` `attr-defined` hatası verir (django-stubs sadece `models.py` tarar). Service/behavior code başka modülde olabilir, sadece model definition `models.py`'da.
- **SECRET_KEY:** Default'u **kaldırıldı**. `DJANGO_SECRET_KEY` env var yoksa container fail-fast. CI'da synthetic secret olarak commit SHA kullanılıyor.
- **SoftDeleteModel kontrat:** `Model.objects` artık deleted satırları **filtreler** (default manager). Audit/admin/restore için `Model.all_objects` kullan. `base_manager_name = "all_objects"` set edildi ki FK reverse lookup'lar (cascade vs.) deleted satırları görsün.
- **Email verification:** Backend tam çalışıyor (token + endpoint + console mail). Production'a çıkmadan önce `EMAIL_BACKEND` Mailgun/Anymail'e çevrilmeli. `User.is_email_verified` read-only API field, register sonrası False, `/auth/verify-email/` ile True.
