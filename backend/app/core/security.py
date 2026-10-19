"""JWT-аутентификация (SDD, раздел 3.4, Приложение A, раздел 11).

- create_access_token — подпись HS256-токена payload'ом
  { "sub": user_id, "store_ids": [1, 2], "exp": ... } (SDD, раздел 3.4);
- decode_access_token  — проверка подписи и срока жизни, возврат
  TokenPayload; при любой ошибке — AuthError (401).

Секрет — settings.JWT_SECRET_KEY (никогда не коммитится, см. .env.example).
Первичный вход — ACCESS_KEY через POST /auth/login.
"""

from datetime import UTC, datetime, timedelta

import jwt

from backend.app.core.config import settings

ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=12)


class AuthError(Exception):
    """Невалидный или отсутствующий JWT (в роутерах -> 401)."""


class TokenPayload:
    """Декодированный payload токена."""

    __slots__ = ("store_ids", "user_id")

    def __init__(self, user_id: int, store_ids: list[int]) -> None:
        self.user_id = user_id
        self.store_ids = store_ids


def create_access_token(user_id: int, store_ids: list[int]) -> str:
    """Выдать JWT для пользователя со списком доступных магазинов."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "store_ids": store_ids,
        "iat": now,
        "exp": now + TOKEN_TTL,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Раскрыть и провалидировать токен; AuthError при любой ошибке."""
    try:
        data = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(data["sub"])
        store_ids = [int(s) for s in data.get("store_ids", [])]
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise AuthError("Невалидный или просроченный токен") from exc
    return TokenPayload(user_id=user_id, store_ids=store_ids)
