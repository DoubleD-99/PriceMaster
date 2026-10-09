"""Аутентификация — POST /auth/login (SDD, Приложение A, раздел 5).

Body:   { "access_key": str }
Response: { "token": str, "user_info": ... }

Выдаёт JWT-токен; дальнейшие запросы — заголовком
`Authorization: Bearer <token>` (плюс `X-Store-ID` для изоляции данных).
401 при неверном access_key. Секрет — ACCESS_KEY из окружения.
"""
