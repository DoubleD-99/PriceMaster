"""Integration-тесты REST API (SDD, Приложение A, раздел 5).

Проверяют на тестовой БД (conftest.py, db_schema + clean_tables):
- POST /auth/login               - выдача JWT по access_key; 401 без него;
- GET  /stores, /products        - справочники под JWT;
- GET  /inventory                - 400 без X-Store-ID, 403 при чужом;
- POST /wms/receiving            - приёмка: партия + остатки, валидация;
- POST /wms/write-off            - списание FIFO по expiry_date (раздел 3.3),
                                   ошибка формата 6.2 при нехватке;
- GET  /barcodes/{code}          - поиск товара по ШК, 404 на неизвестный.

Изоляция магазинов (SDD, раздел 3.4): токен без магазина + X-Store-ID -> 403.
"""

from datetime import datetime, timedelta, timezone

from backend.app.core.config import settings


def _day(offset: int) -> str:
    """Дата ISO (сегодня + offset) — для тел WMS-запросов."""
    return (datetime.now(timezone.utc).date() + timedelta(days=offset)).isoformat()


# =========================
# AUTH
# =========================


async def test_login_wrong_key_401(api_client) -> None:
    response = await api_client.post("/auth/login", json={"access_key": "nope"})
    assert response.status_code == 401


async def test_private_route_without_token_401(api_client) -> None:
    response = await api_client.get("/stores")
    assert response.status_code == 401


async def test_login_returns_jwt_with_store_ids(api_client, shop) -> None:
    response = await api_client.post(
        "/auth/login", json={"access_key": settings.ACCESS_KEY}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user_info"]["store_ids"] == shop["store_ids"]


async def test_garbage_token_401(api_client) -> None:
    response = await api_client.get("/stores", headers={"Authorization": "Bearer xyz"})
    assert response.status_code == 401


# =========================
# TENANT-ISOLATION (SDD 3.4)
# =========================


async def test_foreign_store_header_403(auth_client) -> None:
    response = await auth_client.get("/inventory", headers={"X-Store-ID": "9999"})
    assert response.status_code == 403


async def test_login_before_any_store_rejects_any_header(api_client) -> None:
    """Токен выдан без магазинов -> любой X-Store-ID чужой -> 403."""
    login = await api_client.post(
        "/auth/login", json={"access_key": settings.ACCESS_KEY}
    )
    headers = {
        "Authorization": f"Bearer {login.json()['token']}",
        "X-Store-ID": "1",
    }
    response = await api_client.get("/inventory", headers=headers)
    assert response.status_code == 403


async def test_missing_store_header_400(auth_client) -> None:
    response = await auth_client.get("/inventory")
    assert response.status_code == 400


# =========================
# СПРАВОЧНИКИ
# =========================


async def test_stores_and_products_list(auth_client, shop) -> None:
    stores = await auth_client.get("/stores")
    assert stores.status_code == 200
    assert [row["id"] for row in stores.json()] == shop["store_ids"]

    products = await auth_client.get("/products")
    assert products.status_code == 200
    assert {row["id"] for row in products.json()} == set(shop["product_ids"])


async def test_barcode_lookup(auth_client, shop) -> None:
    found = await auth_client.get("/barcodes/4600000000001")
    assert found.status_code == 200
    assert found.json()["id"] == shop["product_ids"][0]

    missing = await auth_client.get("/barcodes/9999999999999")
    assert missing.status_code == 404


# =========================
# WMS: ПРИЁМКА
# =========================


async def test_receiving_creates_batch_and_inventory(auth_client, shop) -> None:
    payload = {
        "product_id": shop["product_ids"][0],
        "quantity": 20,
        "batch_date": _day(-1),
        "expiry_date": _day(13),
    }
    created = await auth_client.post(
        "/wms/receiving",
        json=payload,
        headers={"X-Store-ID": str(shop["store_ids"][0])},
    )
    assert created.status_code == 201, created.text
    assert created.json()["quantity_added"] == 20

    inventory = await auth_client.get(
        "/inventory", headers={"X-Store-ID": str(shop["store_ids"][0])}
    )
    assert inventory.status_code == 200
    rows = inventory.json()
    assert len(rows) == 1
    assert rows[0]["quantity"] == 20
    assert rows[0]["expiry_date"] == payload["expiry_date"]


async def test_receiving_same_batch_sums_quantity(auth_client, shop) -> None:
    headers = {"X-Store-ID": str(shop["store_ids"][0])}
    payload = {
        "product_id": shop["product_ids"][0],
        "quantity": 5,
        "batch_date": _day(-1),
        "expiry_date": _day(13),
    }
    first = await auth_client.post("/wms/receiving", json=payload, headers=headers)
    second = await auth_client.post("/wms/receiving", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201

    inventory = await auth_client.get("/inventory", headers=headers)
    rows = [r for r in inventory.json() if r["quantity"] > 0]
    assert len(rows) == 1
    assert rows[0]["quantity"] == 10


async def test_receiving_validation_errors(auth_client, shop) -> None:
    headers = {"X-Store-ID": str(shop["store_ids"][0])}
    base = {
        "product_id": shop["product_ids"][0],
        "quantity": 5,
        "batch_date": _day(-1),
        "expiry_date": _day(10),
    }

    zero = await auth_client.post(
        "/wms/receiving", json={**base, "quantity": 0}, headers=headers
    )
    assert zero.status_code == 400
    assert zero.json()["error_code"] == "WMS_INVALID_QUANTITY"

    bad_expiry = await auth_client.post(
        "/wms/receiving", json={**base, "expiry_date": _day(-5)}, headers=headers
    )
    assert bad_expiry.status_code == 400
    assert bad_expiry.json()["error_code"] == "WMS_INVALID_EXPIRY"

    unknown = await auth_client.post(
        "/wms/receiving", json={**base, "product_id": 424242}, headers=headers
    )
    assert unknown.status_code == 404
    assert unknown.json()["error_code"] == "PRODUCT_NOT_FOUND"


# =========================
# WMS: СПИСАНИЕ (FIFO)
# =========================


async def test_write_off_takes_oldest_expiry_first(auth_client, shop) -> None:
    """Списание забирает партию с меньшим expiry_date первой (SDD 3.3)."""
    headers = {"X-Store-ID": str(shop["store_ids"][0])}
    product_id = shop["product_ids"][0]

    for quantity, offset in ((5, 1), (10, 10)):
        await auth_client.post(
            "/wms/receiving",
            json={
                "product_id": product_id,
                "quantity": quantity,
                "batch_date": _day(-2),
                "expiry_date": _day(offset),
            },
            headers=headers,
        )

    response = await auth_client.post(
        "/wms/write-off",
        json={"product_id": product_id, "quantity": 8, "reason": "Истёк срок"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert [b["quantity"] for b in result["batches"]] == [5, 3]
    assert [b["expiry_date"] for b in result["batches"]] == [_day(1), _day(10)]

    inventory = await auth_client.get(
        "/inventory",
        headers={"X-Store-ID": str(shop["store_ids"][0])},
        params={"product_id": product_id},
    )
    by_expiry = {row["expiry_date"]: row["quantity"] for row in inventory.json()}
    assert by_expiry[_day(1)] == 0
    assert by_expiry[_day(10)] == 7


async def test_write_off_insufficient_stock_6_2_format(auth_client, shop) -> None:
    headers = {"X-Store-ID": str(shop["store_ids"][0])}
    product_id = shop["product_ids"][0]
    await auth_client.post(
        "/wms/receiving",
        json={
            "product_id": product_id,
            "quantity": 4,
            "batch_date": _day(-1),
            "expiry_date": _day(10),
        },
        headers=headers,
    )

    response = await auth_client.post(
        "/wms/write-off",
        json={"product_id": product_id, "quantity": 10, "reason": "Порча"},
        headers=headers,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "WMS_INSUFFICIENT_STOCK"
    assert body["details"]["requested"] == 10
    assert body["details"]["available"] == 4


async def test_write_off_validation(auth_client, shop) -> None:
    headers = {"X-Store-ID": str(shop["store_ids"][0])}
    response = await auth_client.post(
        "/wms/write-off",
        json={"product_id": shop["product_ids"][0], "quantity": 1, "reason": "   "},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "WMS_INVALID_REASON"
