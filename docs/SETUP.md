# Local Development Setup

## Prerequisites
- Docker and Docker Compose
- Python 3.12+ (optional for running backend outside Docker)
- Node.js 20+ (optional for running frontend outside Docker)

## Quick Start
```bash
cp .env.example .env
make up
```

Services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Health: `http://localhost:8000/api/v1/health`

## Common Commands
```bash
make test
make format
make lint
make down
```

## Notes
- Docker Compose file is `infra/docker-compose.yml`.
- Backend code is mounted into the container at runtime for fast iteration.
