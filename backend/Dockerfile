# Образ для сервиса api (FastAPI + дашборд). Сборка: docker compose build api
FROM python:3.11-slim

# Рабочая папка и PYTHONPATH: репозиторий кладётся целиком, чтобы были доступны пакеты backend, ai_agent и bot.
WORKDIR /app

# Общие зависимости рантайма
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходники проекта
COPY . .

# API + веб-дашборд слушают порт 8000
EXPOSE 8000

# Запуск FastAPI. При необходимости перед стартом вызывается seed_db (см. docker-compose / README).
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]