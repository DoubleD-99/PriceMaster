"""Pydantic-схемы запросов и ответов API (SDD, раздел 3.1, schemas/).

Валидируемые модели для эндпоинтов Приложения A, раздела 5:
- LoginRequest / TokenResponse  — POST /auth/login;
- StoreOut                      — GET  /stores;
- ProductOut                    — GET  /products;
- InventoryItemOut              — GET  /inventory;
- ReceivingRequest / WriteOffRequest — POST /wms/receiving, /wms/write-off;
- RecommendationOut             — GET  /recommendations;
- SaleOut                       — GET  /analytics/sales.

Схемы переиспользуются роутерами (api/v1) и агентом (services/ai)
для типобезопасного обмена.
"""
