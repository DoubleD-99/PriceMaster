# =========================================================================
# PriceMaster — Makefile быстрого локального запуска
# =========================================================================
# Перед первым запуском:
#   1) python -m venv .venv
#   2) make install
#   3) скопировать .env.example -> .env и заполнить значения
# Зависимость: установленный make (на Windows: `choco install make`, WSL или Git Bash)
# и Node.js + npm для фронтенда (цели web*).
# Переменные окружения подтягиваются из .env.
#
# Активировать venv вручную не нужно и нельзя: каждый рецепт make —
# отдельный процесс, активация не «переживает» его. Поэтому вызываем
# интерпретатор venv напрямую через PY.

.DEFAULT_GOAL := help

-include .env

ifdef OS
PY      ?= .venv\Scripts\python.exe
else
PY      ?= .venv/bin/python
endif
PYTEST  ?= $(PY) -m pytest

.PHONY: help install db db-down api seed test web web-install web-build dc-up dc-down

# Help text is ASCII-only on purpose: it renders correctly under any
# terminal/codepage (cmd cp866, PowerShell, WSL, Git Bash) without tricks.
define _HELP_MESSAGE
  Available commands:
    help        Show this help
    install     Install dependencies (runtime + dev)
    db          Start PostgreSQL only in Docker (for local development)
    db-down     Stop the PostgreSQL container (data is kept)
    seed        Fill DB with synthetic data (3-6 months + external factors)
    api         Run FastAPI locally with auto-reload (port 8000)
    test        Run unit + integration tests
    web-install Install frontend dependencies (npm install)
    web         Run Vite dev server (port 5173, proxy /api -> :8000)
    web-build   Build frontend static assets (web/dist)
    dc-up       Start all Docker services (db, api, web)
    dc-down     Stop Docker services
endef

help:
	@$(info $(_HELP_MESSAGE))
	@cd .

install: ## Установить зависимости (рантайм + dev)
	$(PY) -m pip install -r requirements-dev.txt

db: ## Поднять только PostgreSQL в Docker (для локальной разработки)
	docker compose up -d db

db-down: ## Остановить контейнер PostgreSQL (данные сохраняются)
	docker compose stop db

api: ## Запустить FastAPI локально с автоперезагрузкой (порт 8000)
	$(PY) -m uvicorn backend.app.main:app --host $(API_HOST) --port $(API_PORT) --reload

seed: ## Заполнить БД синтетическими данными (3-6 месяцев + внешние факторы)
	$(PY) -m backend.seed_db

test: ## Прогнать unit + integration тесты
	$(PYTEST) -v

web-install: ## Установить зависимости фронтенда (npm install)
	npm --prefix web install

web: ## Запустить Vite dev-сервер (порт 5173, proxy /api -> :8000)
	npm --prefix web run dev

web-build: ## Собрать статику фронтенда (web/dist)
	npm --prefix web run build

dc-up: ## Поднять все сервисы в Docker (db, api, web)
	docker compose up --build

dc-down: ## Остановить Docker-сервисы
	docker compose down