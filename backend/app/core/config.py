"""Application configuration from environment variables."""

import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_VALUES = {"FORTUNA812", "secret", "supersecret"}
_PLACEHOLDER_MARKERS = ("измените", "change_me", "changeme", "replace", "your-")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@db:5432/pricemaster"
    LLM_API_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    JWT_SECRET_KEY: str = ""
    ACCESS_KEY: str = ""
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 300
    LOGIN_LOCKOUT_SECONDS: int = 900
    TRUST_PROXY_HEADERS: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @field_validator("JWT_SECRET_KEY", "ACCESS_KEY", mode="before")
    @classmethod
    def _strip(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if os.getenv("PRICEMASTER_ALLOW_INSECURE_SECRETS") == "1":
            return self
        for name in ("JWT_SECRET_KEY", "ACCESS_KEY"):
            value = getattr(self, name)
            lowered = value.lower()
            if not value:
                raise ValueError(f"{name} must be set")
            if value in _INSECURE_VALUES or any(
                m in lowered for m in _PLACEHOLDER_MARKERS
            ):
                raise ValueError(f"{name} must be a non-default, non-placeholder value")
        if len(self.JWT_SECRET_KEY) < 16:
            raise ValueError("JWT_SECRET_KEY must be at least 16 characters")
        return self


settings = Settings()
