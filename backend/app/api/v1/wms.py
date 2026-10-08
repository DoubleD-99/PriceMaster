"""Складские операции (WMS) — SDD, Приложение A, разделы 5 и 6.

- POST /wms/receiving — приёмка; Body { product_id, quantity, batch_date,
  expiry_date }: запись партии + обновление остатков;
- POST /wms/write-off — списание; Body { product_id, quantity, reason }:
  фиксация убытка (порча/истечение срока), списание по партиям FIFO
  (срок годности раньше списывается раньше) — раздел 6.3.

Бизнес-логика — в backend.app.services.wms (без HTTP).
Требуется JWT + X-Store-ID; 400 при нехватке остатков/невалидных данных.
"""
