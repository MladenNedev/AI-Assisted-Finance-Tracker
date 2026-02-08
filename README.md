# AI-Assisted Personal Finance Tracker

Production-style modular monolith for internal finance operations. Phase 0 is a scaffold with a health endpoint and UI placeholders.

## Quickstart
1. Copy `.env.example` to `.env` and adjust values.
2. `make up`
3. `make test`
4. `make down`

## Services
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Health: `GET /api/v1/health`

## Structure
- `backend/`: FastAPI + SQLAlchemy async + Alembic
- `frontend/`: Vite + React + Mantine
- `infra/`: docker-compose
- `docs/`: planning and workflow
