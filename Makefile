DC = docker compose --env-file .env -f infra/docker-compose.yml
DC_RUN = $(DC) run --rm --build

.PHONY: up down migrate test format lint

up:
	$(DC) up --build --renew-anon-volumes -d
	@echo "Waiting for PostgreSQL to become ready..."
	$(DC) exec -T postgres sh -lc 'until pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" >/dev/null 2>&1; do sleep 1; done'
	$(MAKE) migrate

migrate:
	$(DC_RUN) backend alembic upgrade head

down:
	$(DC) down -v

test:
	$(DC_RUN) backend pytest

format:
	$(DC_RUN) backend ruff check --fix app tests
	$(DC_RUN) backend black app tests

lint:
	$(DC_RUN) backend ruff check app tests
	$(DC_RUN) backend black --check app tests
