"""Остатки — GET /inventory (SDD, Приложение A, раздел 5).

Текущие остатки с фильтром по store_id (заголовок X-Store-ID):
количество, партии (`batch_date`, `expiry_date`), `min_stock`
на уровне product_id + store_id (Приложение A, раздел 6).

Требуется JWT + X-Store-ID; 400 без/при неверном X-Store-ID.
"""
