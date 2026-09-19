"""Входная точка Telegram-бота.

Запуск поллинга aiogram:
- читает BOT_TOKEN из окружения (config);
- включает middleware контроля доступа (middleware.py);
- регистрирует хендлеры: auth (/start, /auth), report (/report),
  stock_report (/stock_report), daily_summary (/daily_summary),
  product (/product …) и callbacks (кнопки принять/отклонить).

Запуск:  python -m bot   (API backend должен быть запущен).
"""