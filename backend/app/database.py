"""Подключение к базе данных (SQLAlchemy 2.0).

Создаются:
- engine — на основе DATABASE_URL (config);
- SessionLocal — фабрика сессий для роутеров и seed_db;
- Base — базовый класс DeclarativeBase для всех ORM-моделей (models.py).

Также здесь подготавливается папка для Jinja2-шаблонов дашборда.
"""