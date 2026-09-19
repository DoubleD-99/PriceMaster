# Образ для сервиса ai_agent (используется api при генерации рекомендаций).
# Сборка: docker compose build api (агент встраивается в API-сервис) — образ
# оставлен на случай отдельного запуска пайплайна рекомендаций.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Агент не имеет собственного порта: это библиотека-сервис, вызываемая
# из backend (GET /recommendations -> ai_agent.agent.generate_report).
CMD ["python", "-c", "print('ai_agent: библиотека, запускается в составе api')"]