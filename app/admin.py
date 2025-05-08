import json
from math import ceil
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter, CommandStart, Command
from app.admin_keyboards import *
from app.database.requests import get_all_orders, get_orders_by_status, get_order

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


@admin.callback_query(F.data == "admin_orders_status:new")
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


@admin.callback_query(F.data.startswith("admin_orders_status:confirmed"))
async def show_confirmed_orders(callback: CallbackQuery):
    """Показує замовлення зі статусом 'Підтверджено'."""
    orders = await get_orders_by_status("confirmed")

    if not orders:
        await callback.message.edit_text(
            "❌ Немає замовлень зі статусом 'Підтверджено'.",
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
        "✅ Замовлення зі статусом 'Підтверджено':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_confirmed_orders_page:"))
async def process_confirmed_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках замовлень зі статусом 'Підтверджено'."""
    orders = await get_orders_by_status("confirmed")
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "✅ Замовлення зі статусом 'Підтверджено':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_orders_status:shipped"))
async def show_shipped_orders(callback: CallbackQuery):
    """Показує замовлення зі статусом 'Відправлено'."""
    orders = await get_orders_by_status("shipped")

    if not orders:
        await callback.message.edit_text(
            "❌ Немає замовлень зі статусом 'Відправлено'.",
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
        "🚚 Замовлення зі статусом 'Відправлено':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_shipped_orders_page:"))
async def process_shipped_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках замовлень зі статусом 'Відправлено'."""
    orders = await get_orders_by_status("shipped")
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "🚚 Замовлення зі статусом 'Відправлено':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_orders_status:delivered"))
async def show_delivered_orders(callback: CallbackQuery):
    """Показує замовлення зі статусом 'Доставлено'."""
    orders = await get_orders_by_status("delivered")

    if not orders:
        await callback.message.edit_text(
            "❌ Немає замовлень зі статусом 'Доставлено'.",
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
        "📦 Замовлення зі статусом 'Доставлено':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_delivered_orders_page:"))
async def process_delivered_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках замовлень зі статусом 'Доставлено'."""
    orders = await get_orders_by_status("delivered")
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Замовлення зі статусом 'Доставлено':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_orders_status:cancelled_by_admin"))
async def show_cancelled_by_admin_orders(callback: CallbackQuery):
    """Показує замовлення зі статусом 'Скасовано адміністратором'."""
    orders = await get_orders_by_status("cancelled_by_admin")

    if not orders:
        await callback.message.edit_text(
            "❌ Немає замовлень зі статусом 'Скасовано адміністратором'.",
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
        "❌ Замовлення зі статусом 'Скасовано адміністратором':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_cancelled_by_admin_orders_page:"))
async def process_cancelled_by_admin_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках замовлень зі статусом 'Скасовано адміністратором'."""
    orders = await get_orders_by_status("cancelled_by_admin")
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "❌ Замовлення зі статусом 'Скасовано адміністратором':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_orders_status:cancelled_by_user"))
async def show_cancelled_by_user_orders(callback: CallbackQuery):
    """Показує замовлення зі статусом 'Скасовано користувачем'."""
    orders = await get_orders_by_status("cancelled_by_user")

    if not orders:
        await callback.message.edit_text(
            "❌ Немає замовлень зі статусом 'Скасовано користувачем'.",
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
        "❌ Замовлення зі статусом 'Скасовано користувачем':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_cancelled_by_user_orders_page:"))
async def process_cancelled_by_user_orders_pagination(callback: CallbackQuery):
    """Обробляє навігацію по сторінках замовлень зі статусом 'Скасовано користувачем'."""
    orders = await get_orders_by_status("cancelled_by_user")
    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Отримуємо замовлення для поточної сторінки
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "❌ Замовлення зі статусом 'Скасовано користувачем':",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("admin_order_details:"))
async def show_admin_order_details(callback: CallbackQuery):
    """
    Універсальна функція для виводу деталей замовлення адміністраторами.
    """
    order_id = int(callback.data.split(":")[1])  # Отримуємо ID замовлення з callback_data

    # Отримуємо інформацію про замовлення
    order = await get_order(order_id)

    if not order:
        await callback.message.edit_text(
            "❌ Замовлення не знайдено.",
            reply_markup=get_back_to_orders_menu()
        )
        return

    # Форматуємо інформацію про замовлення
    articles = json.loads(order.articles)
    items_text = "\n".join(
        [f"- {article}: {quantity} шт." for article, quantity in articles.items()]
    )

    order_details = (
        f"📦 <b>Деталі замовлення #{order.id}</b>:\n\n"
        f"📅 <b>Дата:</b> {order.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🛒 <b>Товари:</b>\n{items_text}\n\n"
        f"💳 <b>Спосіб оплати:</b> {order.payment_method}\n"
        f"🚚 <b>Доставка:</b> {order.delivery}\n"
        f"📍 <b>Адреса:</b> {order.address}\n"
        f"👤 <b>Отримувач:</b> {order.name}\n"
        f"📞 <b>Телефон:</b> {order.phone}\n"
        f"📌 <b>Статус:</b> {OrderStatus(order.status).get_uk_description()}"
    )

    await callback.message.edit_text(
        order_details,
        reply_markup=get_back_to_orders_menu()
    )
