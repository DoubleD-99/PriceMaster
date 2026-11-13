"""Аутентификация — POST /auth/login (SDD, Приложение A, раздел 5).

Body:   { "access_key": str }
Response: { "token": str, "user_info": ... }

Сверяет access_key с ACCESS_KEY из окружения (сравнение за постоянное
время) и выдаёт JWT payload'ом { sub, store_ids } (SDD, раздел 3.4);
store_ids — все магазины из таблицы `stores`. 401 при неверном ключе;
429 + Retry-After после серии неудач с одного IP (rate limit).
Дальнейшие запросы — `Authorization: Bearer <token>` (+ `X-Store-ID`).
"""

import secrets

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from backend.app.api.deps import DbDep
from backend.app.core.config import settings
from backend.app.core.rate_limit import client_ip, login_limiter
from backend.app.core.security import create_access_token
from backend.app.models import Store
from backend.app.schemas import LoginRequest, TokenResponse, UserInfo

router = APIRouter(tags=["auth"])

USERNAME = "admin"


def _rate_limited(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Слишком много попыток входа. Повторите позже.",
        headers={"Retry-After": str(retry_after)},
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbDep, request: Request) -> TokenResponse:
    """Выдать JWT по мастер-ключу ACCESS_KEY с защитой от перебора."""
    key = client_ip(request)
    retry_after = login_limiter.check(key)
    if retry_after is not None:
        raise _rate_limited(retry_after)

    if not secrets.compare_digest(body.access_key, settings.ACCESS_KEY):
        retry_after = login_limiter.register_failure(key)
        if retry_after is not None:
            raise _rate_limited(retry_after)
        raise HTTPException(status_code=401, detail="Неверный access_key")

    login_limiter.register_success(key)
    store_ids = list((await db.scalars(select(Store.id).order_by(Store.id))).all())
    user_id = 1
    token = create_access_token(user_id=user_id, store_ids=store_ids)
    user_info = UserInfo(user_id=user_id, username=USERNAME, store_ids=store_ids)
    return TokenResponse(token=token, user_info=user_info)
