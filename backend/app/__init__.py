"""Пакет FastAPI-приложения PriceMaster (структура — SDD, раздел 3.1).

- api/       — слой HTTP (deps.py, v1/ — роутеры из Приложения A, раздел 5);
- core/      — конфигурация, security, exceptions;
- db/        — сессия БД и базовый класс ORM;
- models/    — SQLAlchemy ORM-модели (только структура БД, 9 таблиц);
- schemas/   — Pydantic-схемы (Request/Response);
- services/  — бизнес-логика, не зависит от HTTP
               (wms, analytics, calculations, external_factors, ai/).
"""
