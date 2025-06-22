import json
from math import ceil
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter, CommandStart, Command
from app.admin_keyboards import *
from app.database.requests import get_all_orders, get_orders_by_status, get_order, update_order_status
from app.database.products import ProductManager
from app.database.models import OrderStatus
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
            "❌ Немає замовлень зі статусом 'В обробці'.",
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
        "📦 Замовлення зі статусом 'В обробці':",
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
    try:
        order_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        # Можна додати логування помилки тут, якщо потрібно
        await callback.message.edit_text(
            "❌ Помилка: Некоректний ID замовлення.",
            reply_markup=get_back_to_orders_menu()  # Повернення до списку замовлень
        )
        await callback.answer()
        return

    order = await get_order(order_id)

    if not order:
        await callback.message.edit_text(
            "❌ Замовлення не знайдено.",
            reply_markup=get_back_to_orders_menu()
        )
        await callback.answer()
        return

    # Ініціалізуємо ProductManager
    product_manager_instance = ProductManager()

    try:
        articles_dict = json.loads(order.articles)
    except json.JSONDecodeError:
        # Логування помилки
        await callback.message.edit_text(
            "❌ Помилка при завантаженні деталей товарів у замовленні.",
            reply_markup=get_order_details_keyboard(order_id)  # Повернення до деталей з можливістю зміни статусу
        )
        await callback.answer()
        return

    items_text_list = []
    for article_code, quantity in articles_dict.items():
        product_info = product_manager_instance.get_product_info(article_code)
        product_name = product_info[0] if product_info else f"Артикул {article_code}"
        items_text_list.append(f"- {product_name} (Арт: {article_code}): {quantity} шт.")

    items_text = "\n".join(items_text_list) if items_text_list else "Інформація про товари відсутня."

    # Формуємо інформацію про замовлення
    order_details_message = f"📦 <b>Деталі замовлення #{order.id}</b>:\n\n"
    order_details_message += f"📅 <b>Дата:</b> {order.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
    order_details_message += f"👤 <b>Отримувач:</b> {order.name}\n"
    order_details_message += f"📞 <b>Телефон:</b> {order.phone}\n\n"
    order_details_message += f"🛒 <b>Товари:</b>\n{items_text}\n\n"
    order_details_message += f"💰 <b>Сума замовлення:</b> {order.total_price:.2f} грн\n"

    # Додаємо коментар, якщо він є
    if order.comment and order.comment.strip():  # Перевіряємо, що коментар не порожній
        order_details_message += f"💬 <b>Коментар клієнта:</b> {order.comment}\n"

    order_details_message += f"\n💳 <b>Спосіб оплати:</b> {order.payment_method}\n"
    order_details_message += f"🚚 <b>Доставка:</b> {order.delivery}\n"
    order_details_message += f"📍 <b>Адреса:</b> {order.address}\n"
    order_details_message += f"📌 <b>Статус:</b> {OrderStatus(order.status).get_uk_description()}"

    await callback.message.edit_text(
        order_details_message,
        reply_markup=get_order_details_keyboard(order_id),
        parse_mode="HTML"  # Важливо для відображення <b> тегів
    )
    await callback.answer()


@admin.callback_query(F.data.startswith("edit_order_status:"))
async def edit_order_status(callback: CallbackQuery):
    """
    Виводить клавіатуру для зміни статусу замовлення.
    """
    order_id = int(callback.data.split(":")[1])  # Отримуємо ID замовлення
    keyboard = get_change_status_keyboard(order_id)

    await callback.message.edit_text(
        f"✏️ Оберіть новий статус для замовлення #{order_id}:",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("change_order_status:"))
async def change_order_status(callback: CallbackQuery):
    """
    Обрабатывает изменение статуса заказа администратором и возвращает к информации о заказе.

    Args:
        callback (CallbackQuery): Запрос от администратора.
    """
    try:
        # Извлечение информации из callback_data
        _, order_id, new_status = callback.data.split(":")
        order_id = int(order_id)

        # Обновление статуса заказа в базе данных
        updated_order = await update_order_status(order_id, OrderStatus(new_status))

        if not updated_order:
            await callback.answer("❌ Не вдалося оновити статус замовлення.", show_alert=True)
            return

        # Отправка уведомления пользователю
        user_id = updated_order.tg_id  # Получаем Telegram ID пользователя
        status_description = OrderStatus(new_status).get_uk_description()
        notification_message = (
            f"Статус Вашого замовлення #{order_id} змінено на: {status_description}"
        )

        # Отправка сообщения пользователю
        await callback.bot.send_message(chat_id=user_id, text=notification_message)

        # Форматирование информации о заказе
        articles = json.loads(updated_order.articles)
        items_text = "\n".join(
            [f"- {article}: {quantity} шт." for article, quantity in articles.items()]
        )

        order_details = (
            f"📦 <b>Деталі замовлення #{updated_order.id}</b>:\n\n"
            f"📅 <b>Дата:</b> {updated_order.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🛒 <b>Товари:</b>\n{items_text}\n\n"
            f"💰 <b>Сума замовлення:</b> {updated_order.total_price:.2f} грн\n"
            f"💳 <b>Спосіб оплати:</b> {updated_order.payment_method}\n"
            f"🚚 <b>Доставка:</b> {updated_order.delivery}\n"
            f"📍 <b>Адреса:</b> {updated_order.address}\n"
            f"👤 <b>Отримувач:</b> {updated_order.name}\n"
            f"📞 <b>Телефон:</b> {updated_order.phone}\n"
            f"📌 <b>Статус:</b> {OrderStatus(updated_order.status).get_uk_description()}"
        )

        # Получение клавиатуры для деталей заказа
        keyboard = get_order_details_keyboard(order_id)

        # Обновление сообщения с информацией о заказе
        await callback.message.edit_text(
            order_details,
            reply_markup=keyboard
        )

    except Exception as e:
        await callback.answer(f"⚠️ Произошла ошибка: {str(e)}", show_alert=True)
