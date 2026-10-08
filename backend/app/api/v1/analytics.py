"""Аналитика — GET /analytics/sales (SDD, Приложение A, разделы 5 и 9).

История продаж для графиков: агрегация по sales_history
(по дням/товарам) с изоляцией по store_id (X-Store-ID).

Агрегация — в backend.app.services.analytics (без HTTP).
Требуется JWT + X-Store-ID; 401 без токена.
"""
