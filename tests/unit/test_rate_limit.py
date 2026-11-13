"""Unit-тесты ограничителя попыток входа."""

from backend.app.core.rate_limit import LoginRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def test_failures_outside_window_are_ignored() -> None:
    clock = FakeClock()
    limiter = LoginRateLimiter(
        max_attempts=2, window_seconds=10, lockout_seconds=30, clock=clock
    )
    assert limiter.register_failure("ip") is None
    clock.value = 11
    assert limiter.register_failure("ip") is None
    assert limiter.check("ip") is None


def test_lockout_expires() -> None:
    clock = FakeClock()
    limiter = LoginRateLimiter(
        max_attempts=2, window_seconds=10, lockout_seconds=30, clock=clock
    )
    limiter.register_failure("ip")
    assert limiter.register_failure("ip") == 30
    assert limiter.check("ip") == 30
    clock.value = 20
    assert limiter.check("ip") == 10
    clock.value = 31
    assert limiter.check("ip") is None


def test_success_resets_failures() -> None:
    clock = FakeClock()
    limiter = LoginRateLimiter(
        max_attempts=2, window_seconds=10, lockout_seconds=30, clock=clock
    )
    limiter.register_failure("ip")
    limiter.register_success("ip")
    assert limiter.register_failure("ip") is None
