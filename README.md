# Finance Tracker

Full‑stack personal finance tracker built with FastAPI, React, PostgreSQL, and Redis. Implements production‑ready auth, reporting, caching, and CI with a layered architecture.

## Live Demo
- Demo URL: **TBD**
- Demo account: **demo@finance-tracker.app / Demo1234!**

## Screenshot
Capture the dashboard after logging in (summary cards + charts + heatmap + merchants visible).

```
docs/images/dashboard.png
```

## Key Features
- Secure session auth with CSRF, rate limits, and Redis‑backed sessions
- Accounts, transactions, categories, and budgets (including rollover + templates)
- Reporting dashboard: cashflow, category trends, net worth, heatmap, top merchants
- CSV exports (transactions + reporting)
- Observability: Sentry, structured logging, health checks

## Tech Stack
- Backend: FastAPI, SQLAlchemy (async), Alembic, Redis
- Frontend: React, Vite, Mantine, Recharts
- Infra: Docker Compose, Railway
- CI: GitHub Actions

## Architecture (Layered)
```
API (FastAPI)
  -> Services (business logic)
    -> Domain (rules + validation)
      -> Persistence (repositories, models)
```

## Local Development
1. Copy `.env.example` to `.env` and adjust values.
2. `make up`
3. `make test`
4. `make down`

## Services
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Health: `GET /api/v1/health`

## Project Structure
- `backend/`: FastAPI + SQLAlchemy async + Alembic
- `frontend/`: Vite + React + Mantine
- `infra/`: docker‑compose
- `docs/`: planning and workflow
