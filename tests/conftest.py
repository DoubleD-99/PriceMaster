"""Фикстуры pytest.

- app/engine/session — тестовая БД (PostgreSQL в контейнере, либо SQLite для
  простых unit-тестов; полный набор таблиц из backend.app.models);
- mock_llm — замена вызова LLM (openai/Ollama) заранее заданным ответом,
  чтобы integration-тест проверял поток данных, а не модель (ТЗ раздел 6);
- api_client — httpx AsyncClient, указывающий на тестовое FastAPI-приложение.
- bot_fixture — диспетчер aiogram с RAM-хранилищем для проверки хендлеров.
"""
