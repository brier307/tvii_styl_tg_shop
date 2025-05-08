from math import ceil
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter, CommandStart, Command
from app.admin_keyboards import *
from app.database.requests import get_all_orders, get_orders_by_status

from config import ADMIN

admin = Router()
ORDERS_PER_PAGE = 10  # Кількість замовлень на одній сторінці


class Admin(Filter):
    def __init__(self):
        self.admins = ADMIN

    async def __call__(self, message: Message):
        return message.from_user.id in self.admins
    

@admin.message(F.text == "/menu")
async def cmd_menu(message: Message):
    await message.answer('Ласкаво просимо, адміністратор!', reply_markup=get_admin_main_menu())


@admin.callback_query(F.data == "admin_main_menu")
async def show_admin_main_menu(callback: CallbackQuery):
    """Показує головне меню адміністратора."""
    await callback.message.edit_text(
        "Головне меню адміністратора:",
        reply_markup=get_admin_main_menu()
    )


@admin.callback_query(F.data == "admin_orders_menu")
async def show_orders_menu(callback: CallbackQuery):
    """Показує меню замовлень для адміністратора."""
    await callback.message.edit_text(
        "Меню замовлень:",
        reply_markup=get_orders_menu_keyboard()
    )


@admin.callback_query(F.data == "admin_all_orders")
async def show_all_orders(callback: CallbackQuery):
    """Показує всі замовлення для адміністратора."""
    orders = await get_all_orders()

    if not orders:
        await callback.message.edit_text(
            "❌ Немає жодного замовлення.",
            reply_markup=get_back_to_main_menu()
        )
        return

    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = 1

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Усі замовлення:",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_orders_page:"))
async def process_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках усіх замовлень."""
    orders = await get_all_orders()
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Усі замовлення:",
        reply_markup=keyboard
    )


@admin.callback_query(F.data == "admin_new_orders")
async def show_new_orders(callback: CallbackQuery):
    """Показує замовлення зі статусом 'new'."""
    orders = await get_orders_by_status("new")

    if not orders:
        await callback.message.edit_text(
            "❌ Немає замовлень зі статусом 'new'.",
            reply_markup=get_back_to_orders_menu()
        )
        return

    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = 1

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Замовлення зі статусом 'new':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_new_orders_page:"))
async def process_new_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках замовлень зі статусом 'new'."""
    orders = await get_orders_by_status("new")
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Замовлення зі статусом 'new':",
        reply_markup=keyboard
    )

