COMPOSE ?= docker compose
ifeq ($(OS),Windows_NT)
VENV_PYTHON := .venv/Scripts/python
else
VENV_PYTHON := .venv/bin/python
endif
PYTHON ?= $(VENV_PYTHON)

.DEFAULT_GOAL := help
.PHONY: help env install up run start seed seed-demo down logs ps psql test openapi reset

help:
	@echo make env        Create .env from .env.example with generated secrets
	@echo make install    Create .venv and install the backend and test dependencies
	@echo make up         Start app-db, keycloak-db and Keycloak in Docker, and wait until healthy
	@echo make run        Run the backend on the host with reload, at http://localhost:8000/docs
	@echo make start      make up, make seed, then make run
	@echo make seed       Seed reference data
	@echo make seed-demo  Seed reference data and one demo account per role
	@echo make logs       Follow container logs, or one service with: make logs s=keycloak
	@echo make ps         Show container status
	@echo make psql       Open psql on the app database
	@echo make test       Run the backend tests
	@echo make openapi    Regenerate frontend/openapi.json and the TypeScript client
	@echo make down       Stop the containers and keep their data
	@echo make reset      Stop the containers and DELETE both databases

env:
	python scripts/init_env.py

install:
	python -m venv .venv
	$(PYTHON) -m pip install -r requirements-dev.txt

up:
	$(COMPOSE) up -d --wait

run:
	$(PYTHON) -m uvicorn main:app --reload

start: up seed run

seed:
	$(PYTHON) seed.py

seed-demo:
	$(PYTHON) seed.py --demo-users

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f $(s)

ps:
	$(COMPOSE) ps

psql:
	$(COMPOSE) exec app-db psql -U camwa camwa

test:
	$(PYTHON) -m pytest tests -q

openapi:
	$(PYTHON) -m scripts.export_openapi
	cd frontend && npm run openapi:generate

reset:
	$(COMPOSE) down -v
