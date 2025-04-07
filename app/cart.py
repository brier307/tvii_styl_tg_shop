import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject

from app.user_keyboards import *

from app.database.requests import set_user
from app.database.products import ProductManager
from app.database.redis_cart import RedisCart

from app.database.products import ProductManager


product_manager = ProductManager("Stock.xls")

user = Router()
cart = RedisCart()


# Обновляем функцию format_cart_content для более информативного отображения
async def format_cart_content(user_cart: dict, user_id: int) -> str:
    """
    Форматирует содержимое корзины в текстовое сообщение

    Args:
        user_cart (dict): Корзина пользователя
        user_id (int): ID пользователя

    Returns:
        str: Отформатированный текст корзины
    """
    cart_items = []
    total_sum = 0
    invalid_items = []

    for article, quantity in user_cart.items():
        product_info = product_manager.get_product_info(article)
        if not product_info:
            invalid_items.append(article)
            continue

        name, price, available = product_info
        if available < quantity:
            invalid_items.append(article)
            continue

        item_total = price * quantity
        total_sum += item_total

        cart_items.append({
            'name': name,
            'article': article,
            'quantity': quantity,
            'price': price,
            'total': item_total,
            'available': available
        })

    # Если есть недоступные товары, удаляем их
    if invalid_items:
        for article in invalid_items:
            await cart.remove_item(user_id, article)

    # Если все товары оказались недоступны
    if not cart_items:
        return ("🛒 Ваш кошик порожній\n\n"
                "Всі товари виявилися недоступними і були видалені.")

    text = "🛒 Ваш кошик:\n\n"

    for item in cart_items:
        text += (
            f"📦 {item['name']}\n"
            f"Артикул: {item['article']}\n"
            f"Кількість: {item['quantity']} шт.\n"
            f"Ціна: {item['price']:.2f} грн. x {item['quantity']} = {item['total']:.2f} грн.\n"
            f"Доступно: {item['available']} шт.\n\n"
            f"Для видалення натисніть кнопку під товаром 👇\n"
            "➖➖➖➖➖➖➖➖➖➖\n\n"
        )

    text += (
        f"💰 Загальна сума: {total_sum:.2f} грн.\n\n"
        "Оберіть дію:"
    )

    return text
