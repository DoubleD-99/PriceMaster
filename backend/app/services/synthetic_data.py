"""Генерация синтетических данных для заполнения БД (seed).

Функции возвращают ORM-объекты (без id — проставит seed_db.py после flush):
- make_stores / make_products / make_barcodes — справочники;
- make_store_products — цены магазинов (base_cost × наценка категории);
- make_inventory — партии на складе (batch_date, expiry = batch_date +
  shelf_life_days), включая почти истёкшие и залежавшиеся для алёртов;
- make_sales — продажи за N дней с сезонностью, днями недели и
  demand_multiplier из external_factors;
- make_price_history — лёгкие колебания цены в исторический период.

Данные детерминированы (random.Random(42)) — воспроизводимы между запусками.
Используется seed_db.py.
"""

import random
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from backend.app.models import (
    Barcode,
    Inventory,
    PriceHistory,
    Product,
    SalesHistory,
    Store,
    StoreProduct,
)
from backend.app.services.calculations import round_money
from backend.app.services.external_factors import (
    demand_multiplier_for,
    is_public_holiday,
    weather_for,
)

RNG_SEED = 42
HISTORY_DAYS = 180

STORES = [
    ("Магазин «На Лесной»", "ул. Лесная, 12", "Москва"),
    ("Магазин «У Фонтанки»", "наб. Фонтанки, 34", "Санкт-Петербург"),
    ("Магазин «На Баумана»", "ул. Баумана, 8", "Казань"),
]

# (name, category, base_cost, shelf_life_days, min_stock)
CATALOG = [
    ("Молоко 3.2%, 900 мл", "Молочные", "65.00", 14, 20),
    ("Кефир 2.5%, 900 мл", "Молочные", "60.00", 10, 15),
    ("Сыр «Гауда», 300 г", "Молочные", "320.00", 45, 10),
    ("Яйцо С1, 10 шт", "Яйца", "90.00", 25, 20),
    ("Хлеб бородинский", "Хлеб", "45.00", 3, 15),
    ("Филе куриное, охлаждённое", "Мясо", "260.00", 5, 12),
    ("Сосиски молочные, 400 г", "Мясо", "180.00", 7, 10),
    ("Гречка, 900 г", "Бакалея", "75.00", 365, 10),
    ("Макароны спагетти, 450 г", "Бакалея", "60.00", 365, 10),
    ("Помидоры, 1 кг", "Овощи и фрукты", "190.00", 7, 15),
    ("Бананы, 1 кг", "Овощи и фрукты", "110.00", 7, 20),
    ("Вода питьевая, 1.5 л", "Напитки", "35.00", 300, 25),
    ("Мороженое пломбир, 100 г", "Мороженое", "55.00", 90, 20),
    ("Мороженое фруктовый лёд, 80 г", "Мороженое", "35.00", 120, 20),
    ("Квас, 1.5 л", "Напитки", "60.00", 60, 15),
    ("Лимонад, 1 л", "Напитки", "70.00", 120, 15),
    ("Апельсиновый сок, 1 л", "Напитки", "95.00", 30, 12),
    ("Пиво светлое, 0.5 л", "Напитки", "80.00", 90, 12),
    ("Чай чёрный, 25 пакетиков", "Горячие напитки", "120.00", 365, 10),
    ("Кофе молотый, 250 г", "Горячие напитки", "320.00", 365, 8),
    ("Какао, 400 г", "Горячие напитки", "180.00", 365, 8),
    ("Мандарины, 1 кг", "Праздничные", "150.00", 14, 15),
    ("Шампанское, 0.75 л", "Праздничные", "450.00", 365, 6),
    ("Шоколад новогодний, 100 г", "Праздничные", "90.00", 180, 12),
    ("Горошек зелёный, 400 г", "Праздничные", "70.00", 365, 10),
    ("Сельдь слабосолёная, 300 г", "Праздничные", "220.00", 10, 8),
    ("Арбуз, 1 кг", "Овощи и фрукты", "60.00", 10, 20),
    ("Клубника, 500 г", "Овощи и фрукты", "180.00", 5, 10),
    ("Огурцы, 1 кг", "Овощи и фрукты", "120.00", 7, 15),
    ("Зелень, 100 г", "Овощи и фрукты", "45.00", 5, 10),
    ("Суп-пюре грибной, 500 г", "Бакалея", "130.00", 180, 8),
    ("Лапша быстрого приготовления, 90 г", "Бакалея", "35.00", 180, 15),
    ("Печенье овсяное, 300 г", "Кондитерские", "85.00", 90, 12),
    ("Шоколад молочный, 100 г", "Кондитерские", "80.00", 180, 12),
    ("Пряники медовые, 400 г", "Кондитерские", "120.00", 60, 8),
    # --- погодозависимые (лето / жаркая погода) ---
    ("Лимонад классический, 1 л", "Напитки", "55.00", 120, 15),
    ("Кола, 1 л", "Напитки", "75.00", 120, 12),
    ("Айран, 500 мл", "Молочные", "45.00", 7, 10),
    ("Сок яблочный, 1 л", "Напитки", "95.00", 30, 12),
    ("Вишня, 1 кг", "Овощи и фрукты", "220.00", 7, 10),
    ("Персики, 1 кг", "Овощи и фрукты", "250.00", 7, 10),
    # --- погодозависимые (зима / холод) ---
    ("Глинтвейн безалкогольный, 1 л", "Горячие напитки", "110.00", 30, 8),
    ("Чай зелёный, 20 пакетиков", "Горячие напитки", "100.00", 365, 8),
    # --- праздничные / spikes в официальные праздники ---
    ("Оливье готовый, 400 г", "Праздничные", "180.00", 3, 6),
    ("Крабовые палочки, 240 г", "Праздничные", "150.00", 10, 8),
    ("Икра красная, 140 г", "Праздничные", "650.00", 180, 4),
    ("Конфеты новогодние в коробке, 300 г", "Кондитерские", "220.00", 180, 8),
]

CATEGORY_MARKUP = {
    "Молочные": Decimal("1.35"),
    "Яйца": Decimal("1.40"),
    "Хлеб": Decimal("1.50"),
    "Мясо": Decimal("1.40"),
    "Бакалея": Decimal("1.45"),
    "Овощи и фрукты": Decimal("1.50"),
    "Напитки": Decimal("1.60"),
    "Мороженое": Decimal("1.70"),
    "Горячие напитки": Decimal("1.55"),
    "Праздничные": Decimal("1.55"),
    "Кондитерские": Decimal("1.50"),
}

# Во сколько раз категория чувствительнее среднего спроса к погоде.
CATEGORY_WEATHER_DEMAND = {
    "Мороженое": {
        "sunny": Decimal("1.70"),
        "rain": Decimal("0.55"),
        "snow": Decimal("0.35"),
    },
    "Напитки": {
        "sunny": Decimal("1.35"),
        "rain": Decimal("0.85"),
        "snow": Decimal("0.75"),
    },
    "Горячие напитки": {
        "sunny": Decimal("0.80"),
        "rain": Decimal("1.20"),
        "snow": Decimal("1.40"),
    },
    "Овощи и фрукты": {
        "sunny": Decimal("1.15"),
        "rain": Decimal("0.95"),
        "snow": Decimal("0.90"),
    },
    "Кондитерские": {
        "sunny": Decimal("0.95"),
        "rain": Decimal("1.10"),
        "snow": Decimal("1.05"),
    },
    "Хлеб": {
        "sunny": Decimal("1.00"),
        "rain": Decimal("1.05"),
        "snow": Decimal("1.05"),
    },
    "Бакалея": {
        "sunny": Decimal("1.00"),
        "rain": Decimal("1.00"),
        "snow": Decimal("1.05"),
    },
}

# Дополнительный спрос в официальные праздники (не каждые выходные).
CATEGORY_HOLIDAY_DEMAND = {
    "Праздничные": Decimal("1.80"),
    "Напитки": Decimal("1.25"),
    "Кондитерские": Decimal("1.20"),
    "Мясо": Decimal("1.15"),
    "Овощи и фрукты": Decimal("1.10"),
    "Горячие напитки": Decimal("1.10"),
    "Молочные": Decimal("1.05"),
    "Хлеб": Decimal("1.05"),
}


def price_for(base_cost: Decimal, category: str) -> Decimal:
    """Розничная цена = себестоимость × наценка категории (1 знак)."""
    return round_money(base_cost * CATEGORY_MARKUP[category])


def product_demand_multiplier(day: date, product: Product) -> Decimal:
    """Спрос товара: общий множитель магазина × погода × праздник категории."""
    weather = weather_for(day)
    multiplier = demand_multiplier_for(day, weather)
    multiplier *= CATEGORY_WEATHER_DEMAND.get(product.category, {}).get(
        weather, Decimal("1.00")
    )
    if is_public_holiday(day):
        multiplier *= CATEGORY_HOLIDAY_DEMAND.get(product.category, Decimal("1.00"))
    return multiplier


def make_stores() -> list[Store]:
    """2–3 магазина сети (Приложение A, раздел 7)."""
    return [
        Store(name=name, address=address, city=city) for name, address, city in STORES
    ]


def make_products() -> list[Product]:
    """Общий каталог: позиции разных категорий, сроков и профилей спроса."""
    return [
        Product(
            name=name,
            category=category,
            base_cost=round_money(Decimal(base_cost)),
            shelf_life_days=shelf_life,
            min_stock=min_stock,
        )
        for name, category, base_cost, shelf_life, min_stock in CATALOG
    ]


def make_barcodes(products: list[Product]) -> list[Barcode]:
    """Один EAN-подобный штрихкод на товар (уникальный, 13 цифр)."""
    return [
        Barcode(product_id=product.id, code=f"46{index:011d}")
        for index, product in enumerate(products, start=1)
    ]


def make_store_products(
    stores: list[Store],
    products: list[Product],
    rng: random.Random | None = None,
) -> list[StoreProduct]:
    """Цены магазинов: наценка категории + лёгкий разброс ±3% по магазину."""
    rng = rng or random.Random(RNG_SEED)
    rows: list[StoreProduct] = []
    for store in stores:
        for product in products:
            base = price_for(product.base_cost, product.category)
            factor = Decimal(str(round(rng.uniform(-0.03, 0.03), 4)))
            rows.append(
                StoreProduct(
                    store_id=store.id,
                    product_id=product.id,
                    current_price=round_money(base * (1 + factor)),
                    is_active=True,
                )
            )
    return rows


def make_inventory(
    stores: list[Store],
    products: list[Product],
    *,
    today: date,
    rng: random.Random | None = None,
) -> list[Inventory]:
    """Партии остатков.

    - 1–3 партии на товар/магазин, срок годности = batch_date + shelf_life;
    - 2 товара с коротким сроком получают почти истёкшие партии (алёрт <= 3 дней);
    - 1 товар получает залежавшуюся просроченную партию (кандидат на списание);
    - 1 товар получает малый остаток (алёрт quantity < min_stock).
    """
    rng = rng or random.Random(RNG_SEED + 1)
    rows: list[Inventory] = []
    short_life = [p for p in products if p.shelf_life_days <= 14]

    for store_index, store in enumerate(stores):
        expiring_products = short_life[store_index * 2 : store_index * 2 + 2]
        stale_product = products[(store_index * 4 + 3) % len(products)]
        low_stock_product = products[(store_index * 5 + 7) % len(products)]

        for product in products:
            batch_count = rng.randint(1, 3)
            for _ in range(batch_count):
                age = rng.randint(0, max(1, min(product.shelf_life_days // 2, 30)))
                batch_date = today - timedelta(days=age)
                expiry_date = batch_date + timedelta(days=product.shelf_life_days)
                quantity = rng.randint(
                    product.min_stock // 2, max(product.min_stock, 1) * 2
                )

                if product in expiring_products:
                    expiry_date = today + timedelta(days=rng.randint(1, 3))
                    quantity = rng.randint(3, 8)
                elif product is stale_product:
                    expiry_date = today - timedelta(days=rng.randint(1, 5))
                    quantity = rng.randint(2, 5)
                elif product is low_stock_product:
                    quantity = rng.randint(1, max(1, product.min_stock // 5))

                rows.append(
                    Inventory(
                        store_id=store.id,
                        product_id=product.id,
                        quantity=quantity,
                        batch_date=batch_date,
                        expiry_date=expiry_date,
                    )
                )
    return rows


def make_sales(
    stores: list[Store],
    products: list[Product],
    prices: dict[tuple[int, int], Decimal],
    *,
    today: date,
    rng: random.Random | None = None,
) -> list[SalesHistory]:
    """Продажи за HISTORY_DAYS: день недели × сезон/погода × профиль категории."""
    rng = rng or random.Random(RNG_SEED + 2)
    rows: list[SalesHistory] = []
    start = today - timedelta(days=HISTORY_DAYS)

    for store in stores:
        for product in products:
            base_daily = max(1, product.min_stock // 4)
            price = prices[(store.id, product.id)]
            day = start
            while day < today:
                multiplier = product_demand_multiplier(day, product)
                noise = Decimal(str(round(rng.uniform(0.5, 1.5), 2)))
                quantity = int(base_daily * float(multiplier) * float(noise))
                if quantity > 0:
                    sale_price = round_money(
                        price * Decimal(str(round(rng.uniform(0.98, 1.02), 4)))
                    )
                    rows.append(
                        SalesHistory(
                            store_id=store.id,
                            product_id=product.id,
                            quantity_sold=quantity,
                            sale_price=sale_price,
                            sale_date=datetime.combine(day, time(12), tzinfo=UTC),
                        )
                    )
                day += timedelta(days=1)
    return rows


def make_price_history(
    stores: list[Store],
    products: list[Product],
    prices: dict[tuple[int, int], Decimal],
    *,
    today: date,
    rng: random.Random | None = None,
) -> list[PriceHistory]:
    """1–3 изменения цены за исторический период (лёгкие колебания ±10%)."""
    rng = rng or random.Random(RNG_SEED + 3)
    rows: list[PriceHistory] = []
    for store in stores:
        for product in products:
            current = prices[(store.id, product.id)]
            count = rng.randint(1, 3)
            levels = [current]
            for _ in range(count):
                factor = Decimal(str(round(rng.uniform(0.9, 1.1), 4)))
                levels.append(round_money(levels[-1] * factor))
            levels.reverse()
            days_ago = sorted(rng.sample(range(1, HISTORY_DAYS), count), reverse=True)
            for index, days in enumerate(days_ago):
                rows.append(
                    PriceHistory(
                        store_id=store.id,
                        product_id=product.id,
                        old_price=levels[index],
                        new_price=levels[index + 1],
                        changed_at=datetime.combine(
                            today - timedelta(days=days),
                            time(10),
                            tzinfo=UTC,
                        ),
                        recommendation_id=None,
                    )
                )
    return rows
