# LedgrIO — Claude Context

## Proje
Fintech SaaS: borsa/kripto/harcama takibi, CSV/PDF export, bütçe uyarıları.
Repo: https://github.com/batuhanaltog/ledgrIO

## Stack
- **Backend:** Django 5 + DRF + simplejwt + drf-spectacular (Swagger) + Celery + Redis + PostgreSQL
- **Frontend:** React 18 + TypeScript + Vite + TanStack (Query/Router/Table) + shadcn/ui + Tailwind + Recharts + Axios + Zustand
- **Infra:** Docker Compose (backend, frontend, db, redis, celery_worker, celery_beat, flower, nginx)

## Yapı
```
backend/
  apps/          # users, portfolios, assets, transactions, budgets, reports, notifications
  celery_app/    # tasks: report_tasks.py, alert_tasks.py
  common/        # TimestampedModel, decimal_utils, pagination
  config/        # settings/base|development|production, urls, wsgi
frontend/
  src/api/       # Axios client + JWT refresh interceptor
  src/store/     # Zustand auth store
nginx/ docker-compose.yml docker-compose.override.yml
```

## Mevcut Durum (Faz 1 tamamlandı)
- Tüm modeller, migration'lar, CRUD API'lar yazıldı
- `docker-compose up --build` çalışıyor, tüm servisler UP
- Migration'lar backend startup'ında otomatik çalışıyor (`migrate --noinput`)
- Swagger: http://localhost:8000/api/schema/swagger-ui/
- Frontend: http://localhost:3000 (App.tsx placeholder, Faz 3'te doldurulacak)
- Flower: http://localhost:5555

## Sonraki Adım — Faz 2
Window Function / CTE sorgularını test et, django-filter entegrasyonu,
budget alert logic, Celery tasks (report + alert), CSV/PDF generator,
dashboard aggregate endpoint, test coverage %90+.

## Kurallar
- Push'u kullanıcı ister, otomatik push atma
- Migration değişikliğinde `docker-compose run --rm backend python manage.py makemigrations` çalıştır
- Test: `docker-compose exec backend pytest --cov`
