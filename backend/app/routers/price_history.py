"""Роутер GET /price-history/{product_id} — история цен по товару.

Читает price_history для заданного product_id (old_price, new_price,
changed_at, recommendation_id) в хронологическом порядке. Данные уходят в
дашборд для графика и в бот (/product).
"""