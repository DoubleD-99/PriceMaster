"""Аналитика — GET /analytics/sales (SDD, Приложение A, разделы 5 и 9).

История продаж для графиков: агрегация по sales_history
(по дням/товарам) с изоляцией по store_id (X-Store-ID).

Агрегация — в backend.app.services.analytics (без HTTP).
Требуется JWT + X-Store-ID; 401 без токена.

Эндпоинт реализуется в Итерации 3 (SDD, Приложение B, раздел B.3);
роутер создан заранее, чтобы main.py подключал его стабильно.
"""

from fastapi import APIRouter

router = APIRouter(tags=["analytics"])
