DC = docker compose --env-file .env -f infra/docker-compose.yml

.PHONY: up down test format lint

up:
	$(DC) up --build -d

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
