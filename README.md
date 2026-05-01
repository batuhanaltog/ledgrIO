<div align="center">
  <img src="ledgrIO.png" alt="LedgrIO Logo" width="180" />

  <h1>LedgrIO</h1>
  <p><strong>Smart Budget & Portfolio Management</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Django-5.0-092E20?style=flat-square&logo=django&logoColor=white" />
    <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black" />
    <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white" />
    <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" />
    <img src="https://img.shields.io/badge/Celery-5-37814A?style=flat-square&logo=celery&logoColor=white" />
  </p>

  <p>
    Track stocks, crypto, and personal expenses — with portfolio analytics, budget alerts, and scheduled reports.
  </p>
</div>

---

## Features

- **Portfolio Management** — Track stocks, crypto, and cash holdings with real-time allocation charts
- **Transaction Tracking** — Full history with BUY/SELL/EXPENSE/INCOME/DIVIDEND support
- **Smart Budgets** — Category-based spending limits with automated threshold alerts (50% / 80% / 100%)
- **Reports** — Async CSV and PDF export via Celery background tasks
- **Analytics** — Window Functions and CTEs for running balance, P&L, and performance time-series
- **REST API** — Fully documented with OpenAPI 3 / Swagger UI

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Database | PostgreSQL 16 (Window Functions, CTEs) |
| Task Queue | Celery 5 + Redis |
| Auth | JWT via `djangorestframework-simplejwt` |
| API Docs | `drf-spectacular` (Swagger UI) |
| Frontend | React 18 + TypeScript + Vite |
| Routing | TanStack Router |
| Server State | TanStack Query |
| Forms | React Hook Form + Zod |
| Tables | TanStack Table |
| Charts | Recharts |
| UI | shadcn/ui + Tailwind CSS |
| Container | Docker + docker-compose |
| Monitoring | Flower (Celery), Grafana + Prometheus *(Phase 5)* |
| CI/CD | Jenkins *(Phase 5)* |

## Project Structure

```
ledgrIO/
├── backend/
│   ├── apps/
│   │   ├── users/          # Custom email-based auth, JWT
│   │   ├── portfolios/     # Portfolio CRUD + CTE allocation queries
│   │   ├── assets/         # Holdings (stock/crypto/cash)
│   │   ├── transactions/   # Financial events + Window Function queries
│   │   ├── budgets/        # Spending limits + alert logic
│   │   ├── reports/        # Async CSV/PDF generation
│   │   └── notifications/  # In-app notification system
│   ├── celery_app/         # Celery config + tasks
│   ├── common/             # Shared models, pagination, decimal utils
│   ├── config/             # Django settings (base/dev/prod)
│   └── requirements/
├── frontend/
│   └── src/
│       ├── api/            # Axios client + JWT refresh interceptor
│       ├── components/     # UI, charts, tables, forms
│       ├── hooks/          # TanStack Query hooks
│       ├── routes/         # TanStack Router file-based routes
│       ├── schemas/        # Zod validation schemas
│       └── store/          # Zustand (auth state)
├── nginx/                  # Reverse proxy config
├── docker-compose.yml
└── docker-compose.override.yml  # Dev hot-reload
```

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- (Optional for local dev) Python 3.12+, Node 20+

### Run with Docker

```bash
# 1. Clone the repository
git clone https://github.com/batuhanaltog/ledgrIO.git
cd ledgrIO

# 2. Copy environment variables
cp .env.example .env
# Edit .env and set a strong SECRET_KEY

# 3. Start all services (dev mode with hot-reload)
docker-compose up --build

# 4. Run migrations and create a superuser
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### Access

| Service | URL |
|---|---|
| Swagger UI | http://localhost:8000/api/schema/swagger-ui/ |
| Django Admin | http://localhost:8000/admin/ |
| Frontend | http://localhost:3000 |
| Flower (Celery) | http://localhost:5555 |

### Local Backend Development (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements/development.txt

# Set environment variables (or use a .env file)
export DJANGO_SETTINGS_MODULE=config.settings.development
export SECRET_KEY=dev-secret-key
export POSTGRES_DB=ledgrio
export POSTGRES_USER=ledgrio_user
export POSTGRES_PASSWORD=ledgrio_password

python manage.py migrate
python manage.py runserver
```

### Local Frontend Development (without Docker)

```bash
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
# Inside the backend container
docker-compose exec backend pytest --cov --cov-report=term-missing

# Or locally
cd backend
pytest --cov --cov-report=term-missing
```

Coverage target: **90%+** enforced via `.coveragerc`.

## API Overview

All endpoints are prefixed with `/api/v1/`.

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register/`, `POST /auth/login/`, `POST /auth/token/refresh/`, `GET/PUT /auth/profile/` |
| Portfolios | CRUD + `/performance/`, `/allocation/`, `/summary/` |
| Assets | CRUD (filter by portfolio, type, symbol) |
| Transactions | CRUD + `/running-balance/`, `/summary/` |
| Budgets | CRUD + `/status/`, `/overview/` |
| Reports | `POST /reports/generate/` (async), `GET /reports/{id}/download/` |
| Notifications | List, mark-read, mark-all-read |
| Dashboard | `GET /dashboard/summary/` (aggregated) |

Full interactive documentation at `/api/schema/swagger-ui/`.

## Development Roadmap

- [x] **Phase 1** — Foundation: Docker, Django scaffold, all models, CRUD APIs, test suite
- [ ] **Phase 2** — Business logic: Window Functions, CTEs, Celery tasks, CSV/PDF generation, 90%+ coverage
- [ ] **Phase 3** — Frontend: React dashboard, charts, tables, forms, auth flows
- [ ] **Phase 4** — Polish: export flows, notification bell, Nginx prod config, rate limiting
- [ ] **Phase 5** — Observability: Grafana + Prometheus, Jenkins CI/CD pipeline

## Environment Variables

See `.env.example` for all available variables.

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | *required* |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...@db:5432/ledgrio` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Access token TTL | `60` |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token TTL | `7` |
| `VITE_API_BASE_URL` | Frontend API base URL | `http://localhost:8000/api/v1` |

## Contributing

This project is currently in active development. Issues and PRs are welcome once the core phases are complete.

## License

MIT
