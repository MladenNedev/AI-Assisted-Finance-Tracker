DC = docker compose --env-file .env -f infra/docker-compose.yml

.PHONY: up down migrate test format lint

up:
	$(DC) up --build --renew-anon-volumes -d
	@echo "Waiting for PostgreSQL to become ready..."
	$(DC) exec -T postgres sh -lc 'until pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" >/dev/null 2>&1; do sleep 1; done'
	$(MAKE) migrate

migrate:
	$(DC) run --rm backend alembic upgrade head

down:
	$(DC) down -v

test:
	$(DC) run --rm backend pytest

format:
	$(DC) run --rm backend ruff check --fix app tests
	$(DC) run --rm backend black app tests

lint:
	$(DC) run --rm backend ruff check app tests
	$(DC) run --rm backend black --check app tests
