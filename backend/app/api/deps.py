"""Общие зависимости FastAPI (dependency injection)."""

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.errors import ApiError
from backend.app.core.security import TokenPayload
from backend.app.db.session import get_db


async def get_current_user(request: Request) -> TokenPayload:
    payload: TokenPayload | None = getattr(request.state, "user", None)
    if payload is None:
        raise ApiError("UNAUTHORIZED", "Требуется аутентификация", status_code=401)
    return payload


async def get_store_id(
    user: Annotated[TokenPayload, Depends(get_current_user)],
    x_store_id: Annotated[str | None, Header(alias="X-Store-ID")] = None,
) -> int:
    if x_store_id is None:
        raise ApiError(
            "MISSING_STORE_ID",
            "Заголовок X-Store-ID обязателен",
            status_code=400,
        )
    try:
        store_id = int(x_store_id)
    except ValueError as exc:
        raise ApiError(
            "INVALID_STORE_ID",
            "X-Store-ID должен быть целым числом",
            status_code=400,
        ) from exc
    if store_id not in user.store_ids:
        raise ApiError(
            "STORE_FORBIDDEN",
            "Магазин не входит в список доступных для токена",
            status_code=403,
        )
    return store_id


DbDep = Annotated[AsyncSession, Depends(get_db)]
UserDep = Annotated[TokenPayload, Depends(get_current_user)]
StoreDep = Annotated[int, Depends(get_store_id)]
