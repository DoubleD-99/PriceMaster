"""Конфигурация приложения из переменных окружения.

Через pydantic-settings читаются значения из .env / окружения:
- DATABASE_URL       — строка подключения к PostgreSQL;
- LLM_API_URL / LLM_API_KEY / LLM_MODEL — параметры внешнего
  OpenAI-совместимого API (requirements.md §6);
- JWT_SECRET_KEY     — секрет подписи JWT-токенов;
- ACCESS_KEY         — ключ доступа для POST /auth/login;
- API_HOST / API_PORT — адрес привязки для локального запуска.

Здесь же описаны имена полей, чтобы все модули брали настройки из одного места.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@db:5432/pricemaster"
    LLM_API_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    JWT_SECRET_KEY: str = "FORTUNA812"
    ACCESS_KEY: str = "secret"
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 300
    LOGIN_LOCKOUT_SECONDS: int = 900
    TRUST_PROXY_HEADERS: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000


settings = Settings()
