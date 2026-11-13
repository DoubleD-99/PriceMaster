"""Проверки seed-каталога и профилей спроса (погода/праздники)."""

from datetime import date
from decimal import Decimal

from backend.app.models import Product
from backend.app.services.external_factors import (
    is_holiday,
    is_public_holiday,
    weather_for,
)
from backend.app.services.synthetic_data import (
    CATALOG,
    CATEGORY_MARKUP,
    product_demand_multiplier,
)


def _product(category: str) -> Product:
    return Product(
        name=f"Тест {category}",
        category=category,
        base_cost=Decimal("10.00"),
        shelf_life_days=30,
        min_stock=10,
    )


def _day_with_weather(month: int, weather: str) -> date:
    for day_number in range(1, 29):
        day = date(2026, month, day_number)
        if weather_for(day) == weather:
            return day
    raise AssertionError(f"Нет дня с погодой {weather} в месяце {month}")


def test_catalog_has_weather_and_holiday_categories() -> None:
    categories = {item[1] for item in CATALOG}
    assert len(CATALOG) >= 30
    assert categories <= set(CATEGORY_MARKUP)
    assert {"Мороженое", "Горячие напитки", "Праздничные"} <= categories


def test_ice_cream_demand_is_higher_on_sunny_day() -> None:
    ice_cream = _product("Мороженое")
    sunny = _day_with_weather(7, "sunny")
    rainy = _day_with_weather(7, "rain")
    assert product_demand_multiplier(sunny, ice_cream) > product_demand_multiplier(
        rainy, ice_cream
    )


def test_hot_drinks_demand_is_higher_on_snowy_day() -> None:
    hot_drink = _product("Горячие напитки")
    snowy = _day_with_weather(1, "snow")
    sunny = _day_with_weather(1, "sunny")
    assert product_demand_multiplier(snowy, hot_drink) > product_demand_multiplier(
        sunny, hot_drink
    )


def test_holiday_products_spike_on_public_holiday() -> None:
    holiday_product = _product("Праздничные")
    staple = _product("Бакалея")
    new_year = date(2026, 1, 3)
    assert is_public_holiday(new_year)
    assert product_demand_multiplier(
        new_year, holiday_product
    ) > product_demand_multiplier(new_year, staple)


def test_regular_weekend_is_not_public_holiday() -> None:
    weekend = date(2026, 1, 17)
    assert is_holiday(weekend)
    assert not is_public_holiday(weekend)
