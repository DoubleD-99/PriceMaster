"""Unit-тесты генератора внешних факторов.

Проверяют external_factors.py:
- weather_condition соответствует сезону (летом не бывает «снега»);
- выходные и праздники помечаются is_holiday=True;
- demand_multiplier учитывает день недели и погоду (выходной/солнце > будни/дождь);
- покрытие дат: исторический период + будущие 2 недели;
- детерминированность: повторный вызов даёт те же значения.
"""

from datetime import date, timedelta
from decimal import Decimal

from backend.app.services import external_factors as ef


def test_weather_matches_season() -> None:
    assert ef.weather_for(date(2026, 7, 15)) == "sunny"
    assert ef.weather_for(date(2026, 1, 15)) in ("snow", "sunny")
    # Летом (июль) снег невозможен по таблице сезонов
    july = [ef.weather_for(date(2026, 7, day)) for day in range(1, 29)]
    assert "snow" not in july


def test_holidays_and_weekends_flagged() -> None:
    assert ef.is_holiday(date(2026, 1, 1))  # праздник РФ
    assert ef.is_holiday(date(2026, 2, 23))
    assert ef.is_holiday(date(2026, 10, 18))  # воскресенье (2026-10-18 — вс)
    assert not ef.is_holiday(date(2026, 10, 19))  # понедельник, не праздник


def test_demand_multiplier_weekend_vs_weekday_and_weather() -> None:
    weekend = ef.demand_multiplier_for(date(2026, 10, 18), "sunny")
    weekday = ef.demand_multiplier_for(date(2026, 10, 19), "rain")
    assert weekend > weekday
    # Дождь в будний день всегда понижает спрос ниже 1.0
    assert weekday < Decimal("1.00")


def test_demand_multiplier_holiday_bonus() -> None:
    holiday = ef.demand_multiplier_for(date(2026, 1, 1), "snow")
    plain = ef.demand_multiplier_for(date(2026, 1, 15), "snow")
    assert holiday > plain
    assert holiday.as_tuple().exponent == Decimal("0.01").as_tuple().exponent


def test_generate_covers_history_and_forecast() -> None:
    today = date(2026, 10, 19)
    rows = ef.generate([1, 2], today=today, history_days=30)
    dates = {row.date for row in rows}
    assert min(dates) == today - timedelta(days=30)
    assert max(dates) == today + timedelta(days=ef.FORECAST_DAYS)
    # Каждый день × каждый магазин
    assert len(rows) == len(dates) * 2
    assert {row.store_id for row in rows} == {1, 2}
    assert all(
        Decimal("0.50") <= row.demand_multiplier <= Decimal("3.00") for row in rows
    )


def test_generate_is_deterministic() -> None:
    today = date(2026, 10, 19)
    first = ef.generate([1], today=today, history_days=10)
    second = ef.generate([1], today=today, history_days=10)
    assert [(r.date, r.weather_condition, r.demand_multiplier) for r in first] == [
        (r.date, r.weather_condition, r.demand_multiplier) for r in second
    ]
