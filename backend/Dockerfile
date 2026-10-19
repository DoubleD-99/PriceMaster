# Образ для сервиса api. Сборка: docker compose build api
FROM python:3.11-slim

# Рабочая папка и PYTHONPATH: контекст сборки — корень репозитория,
# чтобы были доступны пакеты backend (см. docker-compose.yml).
WORKDIR /app

# Общие зависимости рантайма
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходники проекта
COPY . .

# API слушает порт 8000
EXPOSE 8000

# Запуск FastAPI: перед стартом применяются миграции схемы (alembic upgrade
# head), затем uvicorn. Seed данных — вручную: docker compose run api python -m backend.seed_db
CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
