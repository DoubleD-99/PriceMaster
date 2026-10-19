"""Общие зависимости FastAPI (dependency injection).

- get_db           — сессия БД на запрос (делегирует db.session.get_db);
- get_current_user — профиль из request.state.user (TenantMiddleware);
                     401, если middleware не запускался/токен не проверен;
- get_store_id     — обязательный заголовок X-Store-ID текущего запроса:
                     400, если заголовок отсутствует; повторная сверка
                     с store_ids токена -> 403 (SDD, раздел 3.4).

Защита приватных маршрутов: Authorization: Bearer <JWT> + X-Store-ID
(SDD, Приложение A, разделы 3 и 5). Выдача токена — POST /auth/login.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import TokenPayload
from backend.app.db.session import get_db


async def get_current_user(request: Request) -> TokenPayload:
    """Профиль пользователя из request.state.user (кладёт TenantMiddleware)."""
    payload: TokenPayload | None = getattr(request.state, "user", None)
    if payload is None:
        raise HTTPException(status_code=401, detail="Требуется аутентификация")
    return payload


async def get_store_id(
    user: Annotated[TokenPayload, Depends(get_current_user)],
    x_store_id: Annotated[str | None, Header(alias="X-Store-ID")] = None,
) -> int:
    """Текущий магазин из X-Store-ID (400 без заголовка, 403 при чужом)."""
    if x_store_id is None:
        raise HTTPException(status_code=400, detail="Заголовок X-Store-ID обязателен")
    try:
        store_id = int(x_store_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="X-Store-ID должен быть целым числом"
        ) from exc
    if store_id not in user.store_ids:
        raise HTTPException(
            status_code=403, detail="Магазин не входит в список доступных для токена"
        )
    return store_id


DbDep = Annotated[AsyncSession, Depends(get_db)]
UserDep = Annotated[TokenPayload, Depends(get_current_user)]
StoreDep = Annotated[int, Depends(get_store_id)]
