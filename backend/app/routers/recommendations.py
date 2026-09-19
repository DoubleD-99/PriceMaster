"""Роутер GET /recommendations — получение последних советов от агента.

Отдаёт рекомендации из price_recommendations (с товарами), отсортированные
по created_at DESC. Опциональный параметр status позволяет фильтровать
(pending / accepted / rejected) для бота и дашборда.
"""