# Ledgr.io

Akıllı bütçe ve portföy yönetimi platformu (Fintech SaaS).

## Stack

- **Backend:** Django 5 + DRF, PostgreSQL 16, Redis 7, Celery
- **Frontend:** React 18 + Vite + TypeScript, TanStack Query, ShadcnUI, Tailwind
- **DevOps:** Docker Compose

## Hızlı Başlangıç

```bash
cp .env.example .env
docker-compose up --build
```

- API: http://localhost:8000/api/v1/
- Health: http://localhost:8000/api/v1/health/
- API Docs (Swagger): http://localhost:8000/api/v1/docs/
- Frontend (dev): http://localhost:5173

## Komutlar

```bash
# Test
docker-compose exec backend pytest --cov=. --cov-report=term-missing

# Lint
docker-compose exec backend ruff check .
docker-compose exec backend mypy .

# Migration
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py makemigrations
```

Mimari, kurallar ve faz planı için bkz. [`CLAUDE.md`](./CLAUDE.md).
