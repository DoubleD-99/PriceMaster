"""AI и рекомендации — SDD, Приложение A, раздел 5.

- POST /recommendations/generate — запуск анализа агентом: цикл tool
  calling (раздел 3.2.1), результат сохраняется в price_recommendations
  со статусом pending; расчёты выполняются только tools
  (services/calculations.py), LLM пишет лишь обоснование (раздел 3.2);
- GET /recommendations — список рекомендаций (фильтр по status:
  pending / accepted / rejected, сортировка по created_at DESC);
- POST /recommendations/{id}/accept — принять рекомендацию: обновляет
  цену (store_products + запись в price_history с recommendation_id)
  и статус на accepted; отклонение — rejected (без изменения цены).

Принятие/отклонение — human-in-the-loop подтверждение (4-й вызов
confirm_action, раздел 6.1). Требуется JWT + X-Store-ID; 404 на
неизвестный id, 409 при повторной обработке.
"""
