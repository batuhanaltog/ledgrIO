# Ledgr.io — Claude Code Project Guide

---

## 📍 Current State

| Key | Value |
|---|---|
| **Active Phase** | 5 — Budgets + Alerts |
| **Last Completed** | Phase 4.5 — Accounts + Debts + Recurring (2026-05-01) |
| **Next Action** | Phase 5 plan: Budget model + threshold alert service skeleton |
| **Open Decisions** | Budget recurring projection: recurring template'leri usage hesabında say? |
| **Tech Debt / Known Issues** | None |

> **Session başlangıcında bu bloğu oku, sonra bootstrap prompt'u uygula.**

---

## 🚀 Project Overview

Personal/family-scale finance tracker — income/expense, multi-account balance, debts, recurring entries, budgets and alerts. Single-user or small household is the design point. **Multi-tenant SaaS assumptions are out of scope** (see `docs/ARCHITECTURE_RULES.md` §0).

**Stack:** Django 5 (DRF) · PostgreSQL 16 · Redis 7 · Celery · React 18/Vite/TS (Phase 6+) · Docker  
**Key focus:** Financial precision (Decimal), correctness over scale, disciplined testing.

---

## 🔁 Session Workflow

### Bootstrap Prompt (kopyala-yapıştır, her /clear sonrası)

```
Yeni session. Sırayla yap, kod yazma:
1. CLAUDE.md "Current State" bloğunu özetle.
2. docs/decisions.md'nin son 3 kararını oku.
3. Aktif faz için ilk somut adımı öner (plan, implementasyon değil).
4. Onay bekle.
Not: docs/lessons.md'deki kararlar bilinçli trade-off'lardır — değiştirmeyi önermeden önce sor.
```

### Faz Başlangıç Prompt'u (yeni faz açılırken)

```
Faz N başlıyor. Kod yazmadan önce şunları üret:
1. Model şeması (alanlar + tipler + ilişkiler + constraint'ler)
2. Endpoint listesi (URL + method + amaç + auth)
3. Service fonksiyon imzaları (input/output tipleri)
4. Test stratejisi (ne mock'lanacak, coverage hedefi)
Onayladıktan sonra TDD ile implementasyona geç.
```

### Faz Bitiş Prompt'u (DoD sonrası dokümantasyon)

```
Faz N tamamlandı. Şu güncellemeleri yap, önce diff göster:
1. CLAUDE.md → "Current State" bloğunu güncelle (Active Phase = N+1)
2. CLAUDE.md → Faz tablosunda N'i ✅ yap + kısa özet
3. CLAUDE.md → "Endpoints (live)" listesine yeni endpoint'leri ekle
4. CLAUDE.md → Mevcut test/coverage sayısını güncelle
5. docs/lessons.md → Yeni öğrenimler varsa ekle
6. docs/decisions.md → Yeni mimari kararları ADR olarak ekle
Sonra: git tag phase-N-complete && DB backup.
```

---

## ✅ Definition of Done (her faz için)

- [ ] Tüm endpoint'ler çalışıyor ve Swagger'da görünüyor
- [ ] `pytest --cov-fail-under=80` geçiyor (proje geneli)
- [ ] services/selectors %90+, views %75+ (manuel audit)
- [ ] `ruff check .` temiz
- [ ] `mypy .` 0 hata
- [ ] ARCHITECTURE_RULES.md ihlali yok
- [ ] CLAUDE.md "Current State" güncellendi
- [ ] Yeni endpoint'ler "Endpoints (live)" listesine eklendi
- [ ] Yeni öğrenimler `docs/lessons.md`'e eklendi
- [ ] Yeni kararlar `docs/decisions.md`'e ADR olarak eklendi
- [ ] Manuel smoke test: en az 1 happy path curl/Postman
- [ ] `git tag phase-N-complete` atıldı
- [ ] DB backup alındı

---

## 🛠 Build & Run Commands

```bash
docker compose up -d --build          # stack başlat
docker compose exec backend pytest --cov=. --cov-report=term-missing
docker compose exec backend ruff check .
docker compose exec backend mypy .
docker compose exec backend python manage.py migrate
docker compose down -v && docker compose up -d   # dev DB sıfırla
```

**Endpoints (live):**
- Health: `GET /api/v1/health/`
- Swagger: `GET /api/v1/docs/`
- Auth: `POST /api/v1/auth/{register,login,refresh,logout,verify-email,password-reset,password-reset/confirm}/`
- Users: `GET/PATCH /api/v1/users/me/`
- Currencies: `GET /api/v1/currencies/` · `GET /api/v1/fx/?base=X&quote=Y[&date=Z]`
- Accounts: `GET/POST /api/v1/accounts/` · `GET/PATCH/DELETE /api/v1/accounts/<pk>/` · `GET /api/v1/accounts/summary/`
- Transactions: `GET/POST /api/v1/transactions/` · `GET/PATCH/DELETE /api/v1/transactions/<pk>/` · `GET /api/v1/transactions/summary/`
- Categories: `GET/POST /api/v1/categories/` · `GET/PATCH/DELETE /api/v1/categories/<pk>/`
- Debts: `GET/POST /api/v1/debts/categories/` · `PATCH/DELETE /api/v1/debts/categories/<pk>/` · `GET/POST /api/v1/debts/` · `GET/PATCH/DELETE /api/v1/debts/<pk>/` · `POST /api/v1/debts/<pk>/payments/` · `DELETE /api/v1/debts/<pk>/payments/<ppk>/` · `GET /api/v1/debts/monthly-summary/`
- Recurring: `GET/POST /api/v1/recurring/` · `GET/PATCH/DELETE /api/v1/recurring/<pk>/`

---

## 🏗 Architectural Rules (Strict)

Full ruleset: `docs/ARCHITECTURE_RULES.md` — **source of truth.**

- **Layers:** View → validates + delegates · Service → all writes + business logic · Selector → all reads · Model → data + constraints only
- **Financial Precision:** `DecimalField(20,8)` · `decimal.Decimal` · `ROUND_HALF_EVEN` · single quantize at chain end · `common/money.py:q()` only
- **Atomicity:** ≥2 row mutations → `@transaction.atomic`
- **No N+1:** `select_related` / `prefetch_related` / `Subquery` annotations on list endpoints
- **Soft Delete:** `Model.objects` filters deleted. `Model.all_objects` for admin/audit. Hard delete banned on financial data.
- **Response Shape:** List = paginated · Detail/Create/Update = bare object · Errors = `{"error": {"type", "detail", "status"}}`
- **Beat tasks:** data migration only (no `CELERY_BEAT_SCHEDULE`)
- **Frozen phases:** Completed phases are bug-fix-only. New features open a new phase.

---

## 🧪 Testing Standards

| Layer | Floor | Enforcement |
|---|---|---|
| services + selectors | 90% | Manuel audit, faz sonu |
| views | 75% | Manuel audit, faz sonu |
| Project-wide | 80% | CI `--cov-fail-under=80` |

- Financial-calc endpoints: 5 test types (happy, auth, ownership, validation, edge)
- Pure CRUD: 3 types (happy, auth, ownership)
- **Current:** 178 tests · 83% coverage · 0 mypy errors (post Phase 4.5)

---

## 🛟 Backup

- `scripts/backup_postgres.sh` — daily `pg_dump` + 7-day rotation (host cron, Docker dışı)
- Off-site copy: rclone / S3 / Backblaze
- `docs/runbooks/restore-from-backup.md` — restore drill en az 1 kez yapılmalı

---

## 📝 Code Style

- Backend: PEP 8, ruff, descriptive method names
- Frontend: Tailwind, `interface` over `type` for object shapes
- Git: atomic commits with prefix (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- Git tags: `phase-N-start` faz başında, `phase-N-complete` faz sonunda

---

## 📦 Repo Layout

```
ledgrIO/
├── CLAUDE.md                          # bu dosya — session başlangıç referansı
├── docker-compose.yml
├── backend/
│   ├── common/                        # exceptions, money helpers, abstract models
│   └── apps/
│       ├── users/        currencies/  categories/  transactions/
│       ├── accounts/     debts/       recurring/
│       └── budgets/                   # Phase 5 — gelecek
├── docs/
│   ├── ARCHITECTURE_RULES.md          # binding rules
│   ├── decisions.md                   # ADR — mimari kararlar
│   ├── lessons.md                     # öğrenilen dersler + bilinçli trade-off'lar
│   ├── runbooks/                      # restore-from-backup.md
│   └── superpowers/specs/             # faz tasarım dokümanları
├── scripts/
│   └── backup_postgres.sh
└── frontend/                          # Phase 6+
```

---

## 🗺️ Phase Plan

| Phase | Status | Notes |
|---|---|---|
| 1. Repo + Docker | ✅ Done | Health endpoint, postgres/redis/celery |
| 2. Auth/Users (JWT) | ✅ Done | Email login, UserProfile, verify-email |
| 3. Currencies + FX | ✅ Done | Frankfurter, daily beat 06:30 UTC, Redis cache |
| 3.5. Hardening | ✅ Done | Ratelimit, error taxonomy, mypy clean, CI |
| 4. Transactions + Categories | ✅ Done | FX snapshot, filters, summary. ~45 tests, 93% cov |
| 4.5. Accounts + Debts + Recurring | ✅ Done | Atomic payment flow, idempotent beat 03:00 UTC, password reset, backup infra. 178 tests, 83% cov |
| **5. Budgets + Alerts** | ⏳ **Next** | Category-based, date_from/date_to, live usage via Subquery, Celery beat email alert |
| 6. Frontend skeleton + Auth | ⏳ Planned | Vite/React/TS, Tailwind, ShadcnUI |
| 7. Frontend dashboard | ⏳ Planned | TanStack Query, category chart, RHF+Zod |
| 8+. Investments, Reports, Observability | — | |

---

## 📚 Reference Docs

| Doc | İçerik |
|---|---|
| `docs/ARCHITECTURE_RULES.md` | Binding rules: layers, precision, N+1, atomicity, soft delete |
| `docs/decisions.md` | ADR: mimari kararlar ve gerekçeleri |
| `docs/lessons.md` | Öğrenilen dersler + bilinçli trade-off'lar |
| `docs/runbooks/restore-from-backup.md` | DB restore procedure |
