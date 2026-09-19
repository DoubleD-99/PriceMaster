# Образ для сервиса bot (Telegram). Сборка: docker compose build bot
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Бот не слушает порт: работает через поллинг к Telegram (API_URL берётся из env).
CMD ["python", "-m", "bot"]