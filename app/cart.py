# app/cart.py
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject

from app.user_keyboards import *

from app.database.requests import set_user
from app.database.products import ProductManager
from app.database.redis_cart import RedisCart

from app.database.products import ProductManager


product_manager = ProductManager()

user = Router()
cart = RedisCart()


async def format_cart_content(user_cart: dict, user_id: int) -> str:
    """
    Форматирует содержимое корзины в текстовое сообщение.
    Args:
        user_cart (dict): Корзина пользователя {штрих-код: количество}.
    """
    cart_items = []
    total_sum = 0
    invalid_items = []

    for barcode, quantity in user_cart.items():
        product_info = await product_manager.get_product_info_by_barcode(barcode)
        if not product_info:
            invalid_items.append(barcode)
            continue

        name, price, available, article = product_info
        if available < quantity:
            # Можно добавить логику для уменьшения количества до доступного
            # или просто считать товар невалидным для простоты
            invalid_items.append(barcode)
            continue

        item_total = price * quantity
        total_sum += item_total

        cart_items.append({
            'name': name,
            'barcode': barcode,
            'article': article,
            'quantity': quantity,
            'price': price,
            'total': item_total,
            'available': available
        })

    if invalid_items:
        for barcode in invalid_items:
            await cart.remove_item(user_id, barcode)
        # Если после удаления невалидных товаров корзина опустела
        if not cart_items and invalid_items:
             return ("🛒 Ваш кошик пустий\n\n"
                "Деякі товари виявились недоступні та були видалені.")

    if not cart_items:
        return "🛒 Ваша корзина пуста"

    text = "🛒 Ваша корзина:\n\n"
    for item in cart_items:
        text += (
            f"📦 {item['name']}\n"
            f"Артикул: {item['article']}\n"
            f"Штрих-код: {item['barcode']}\n"
            f"Кількість: {item['quantity']} шт.\n"
            f"Ціна: {item['price']:.2f} грн. x {item['quantity']} = {item['total']:.2f} грн.\n"
            f"Доступно: {item['available']} шт.\n"
            "➖➖➖➖➖➖➖➖➖➖\n\n"
        )
    text += f"💰 Загальна сумма: {total_sum:.2f} грн.\n\nОберіть дію:"
    return text

