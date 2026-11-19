"""Ограничение попыток входа (защита от brute-force и простых ботов).

Состояние хранится в памяти процесса: для одного API-инстанса этого достаточно,
при нескольких workers нужен общий backend (Redis) — см. docs/requirements.md §5.
"""

import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request

from backend.app.core.config import settings


@dataclass
class _AttemptState:
    failures: deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


class LoginRateLimiter:
    """Скользящее окно неудачных попыток + временная блокировка ключа."""

    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: float,
        lockout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        self._states: dict[str, _AttemptState] = {}

    def check(self, key: str) -> int | None:
        """Секунды до разблокировки или None, если попытка разрешена."""
        now = self._clock()
        state = self._states.get(key)
        if state is None:
            return None
        if state.blocked_until > now:
            return max(1, math.ceil(state.blocked_until - now))
        self._drop_expired(key, state, now)
        return None

    def register_failure(self, key: str) -> int | None:
        """Учесть неудачу; вернуть секунды блокировки, если лимит исчерпан."""
        now = self._clock()
        state = self._states.setdefault(key, _AttemptState())
        state.failures.append(now)
        self._drop_expired(key, state, now)
        if len(state.failures) >= self.max_attempts:
            state.failures.clear()
            state.blocked_until = now + self.lockout_seconds
            return max(1, math.ceil(self.lockout_seconds))
        return None

    def register_success(self, key: str) -> None:
        """Успешный вход сбрасывает историю неудач."""
        self._states.pop(key, None)

    def reset(self) -> None:
        """Очистить состояние (тесты, перезапуск)."""
        self._states.clear()

    def _drop_expired(self, key: str, state: _AttemptState, now: float) -> None:
        while state.failures and now - state.failures[0] > self.window_seconds:
            state.failures.popleft()
        if not state.failures and state.blocked_until <= now:
            self._states.pop(key, None)


login_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
    lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
)


def client_ip(request: Request) -> str:
    """IP клиента; X-Forwarded-For учитывается только при доверии прокси."""
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
