"""Роутер POST /sales — внесение данных о продаже.

Принимает product_id, quantity_sold, sale_price; фиксирует запись в
sales_history и уменьшает остаток в inventory (в рамках транзакции).
Ответ — сохранённая запись продажи.
"""
