"""Аутентификация - POST /auth/login."""

import secrets

from fastapi import APIRouter, Request
from sqlalchemy import select

from backend.app.api.deps import DbDep
from backend.app.api.errors import ApiError
from backend.app.core.config import settings
from backend.app.core.rate_limit import client_ip, login_limiter
from backend.app.core.security import create_access_token
from backend.app.models import Store
from backend.app.schemas import ErrorResponse, LoginRequest, TokenResponse, UserInfo

router = APIRouter(tags=["Аутентификация"])

USERNAME = "admin"


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Вход по access key",
    description="Проверяет ACCESS_KEY и выдаёт JWT со списком доступных магазинов.",
    responses={
        401: {"model": ErrorResponse, "description": "Неверный access key"},
        429: {"model": ErrorResponse, "description": "Слишком много попыток входа"},
    },
)
async def login(body: LoginRequest, db: DbDep, request: Request) -> TokenResponse:
    key = client_ip(request)
    retry_after = login_limiter.check(key)
    if retry_after is not None:
        raise ApiError(
            "RATE_LIMITED",
            "Слишком много попыток входа. Попробуйте позже.",
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    if not secrets.compare_digest(
        body.access_key.encode("utf-8"), settings.ACCESS_KEY.encode("utf-8")
    ):
        retry_after = login_limiter.register_failure(key)
        if retry_after is not None:
            raise ApiError(
                "RATE_LIMITED",
                "Слишком много попыток входа. Попробуйте позже.",
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        raise ApiError("INVALID_ACCESS_KEY", "Неверный access_key", status_code=401)

    login_limiter.register_success(key)
    store_ids = list((await db.scalars(select(Store.id).order_by(Store.id))).all())
    user_id = 1
    token = create_access_token(user_id=user_id, store_ids=store_ids)
    user_info = UserInfo(user_id=user_id, username=USERNAME, store_ids=store_ids)
    return TokenResponse(token=token, user_info=user_info)
