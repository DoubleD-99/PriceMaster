"""Конфигурация бота из переменных окружения.

- BOT_TOKEN — токен Telegram от @BotFather;
- ACCESS_KEY — секретный ключ для /auth (см. ТЗ, раздел 5);
- API_URL — адрес backend FastAPI (эндпоинты /recommendations, /products, …).
Значения читаются из .env / окружения через os.environ (может использоваться
pydantic-settings как в backend).
"""