"""Роутеры версии API v1 (SDD, Приложение A, раздел 5).

Монтируются в main.py. Общего префикса нет — пути совпадают
с Приложением A один в один:

- auth.py            POST  /auth/login;
- stores.py          GET   /stores;
- products.py        GET   /products;
- inventory.py       GET   /inventory;
- wms.py             POST  /wms/receiving, POST  /wms/write-off;
- barcodes.py        GET   /barcodes/{code};
- recommendations.py POST  /recommendations/generate,
                     GET   /recommendations,
                     POST  /recommendations/{id}/accept;
- analytics.py       GET   /analytics/sales.

Коды ответов: 200/201 — успех, 400 — невалидные данные/неверный заголовок,
401 — нет JWT, 404 — ресурс не найден (SDD, Приложение A, раздел 5).
"""
