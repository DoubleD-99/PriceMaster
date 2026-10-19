"""Генератор синтетических внешних факторов (external_factors).

По ТЗ (раздел 3):
- погода (rain / sunny / snow) с привязкой к сезону;
- пометка выходных и праздничных дней;
- расчёт demand_multiplier по погоде и дню недели;
- покрытие ИСТОРИИ (для обучения/тестов агента) и БУДУЩИХ 2 НЕДЕЛЬ (для прогноза).

Детерминированный генератор (random.seed = порядковый номер дня),
которым пользуется seed_db.py: повторный запуск даёт те же данные.
"""

from datetime import date, timedelta
from decimal import Decimal

from backend.app.models import ExternalFactor

# Праздничные/нерабочие дни РФ (месяц, день).
RU_HOLIDAYS = frozenset(
    {
        (1, 1),
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
        (1, 6),
        (1, 7),
        (1, 8),
        (2, 23),
        (3, 8),
        (5, 1),
        (5, 9),
        (6, 12),
        (11, 4),
    }
)

WEATHER_BY_MONTH = {
    12: ("snow", "snow", "sunny"),
    1: ("snow", "snow", "sunny"),
    2: ("snow", "rain", "sunny"),
    3: ("rain", "rain", "sunny"),
    4: ("rain", "sunny", "sunny"),
    5: ("sunny", "sunny", "rain"),
    6: ("sunny", "sunny", "rain"),
    7: ("sunny", "sunny", "rain"),
    8: ("sunny", "sunny", "rain"),
    9: ("rain", "rain", "sunny"),
    10: ("rain", "rain", "snow"),
    11: ("rain", "snow", "snow"),
}

WEATHER_DEMAND: dict[str, Decimal] = {
    "sunny": Decimal("1.05"),
    "rain": Decimal("0.90"),
    "snow": Decimal("0.85"),
}

WEEKDAY_DEMAND = (1.00, 0.95, 0.95, 1.00, 1.10, 1.20, 1.15)  # пн..вс
HOLIDAY_BONUS = Decimal("1.30")
FORECAST_DAYS = 14


def weather_for(day: date) -> str:
    """Погода дня: детерминированная выборка из сезонного набора."""
    variants = WEATHER_BY_MONTH[day.month]
    return variants[day.toordinal() % len(variants)]


def is_holiday(day: date) -> bool:
    """Выходной или официальный праздник РФ."""
    return day.weekday() >= 5 or (day.month, day.day) in RU_HOLIDAYS


def demand_multiplier_for(day: date, weather: str) -> Decimal:
    """demand_multiplier = погода × день недели × (праздник, если есть)."""
    mult = WEATHER_DEMAND[weather] * Decimal(str(WEEKDAY_DEMAND[day.weekday()]))
    if is_holiday(day):
        mult *= HOLIDAY_BONUS
    return mult.quantize(Decimal("0.01"))


def generate(
    store_ids: list[int],
    *,
    today: date,
    history_days: int = 180,
) -> list[ExternalFactor]:
    """Строки external_factors: история (history_days) + будущие 2 недели."""
    rows: list[ExternalFactor] = []
    start = today - timedelta(days=history_days)
    end = today + timedelta(days=FORECAST_DAYS)
    day = start
    while day <= end:
        weather = weather_for(day)
        for store_id in store_ids:
            rows.append(
                ExternalFactor(
                    store_id=store_id,
                    date=day,
                    weather_condition=weather,
                    is_holiday=is_holiday(day),
                    demand_multiplier=demand_multiplier_for(day, weather),
                )
            )
        day += timedelta(days=1)
    return rows


__all__ = [
    "FORECAST_DAYS",
    "demand_multiplier_for",
    "generate",
    "is_holiday",
    "weather_for",
]
