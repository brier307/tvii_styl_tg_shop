import json
import re
from math import ceil
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter, CommandStart, Command
from app.admin_keyboards import *
from app.database.requests import get_all_orders, get_orders_by_status, get_order, update_order_status
from app.database.products import ProductManager
from app.database.models import OrderStatus
from app.states import AdminOrderStates
from config import ADMIN
import logging

admin = Router()
ORDERS_PER_PAGE = 10  # Кількість замовлень на одній сторінці

logger = logging.getLogger(__name__)


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
        items_dict = json.loads(order.articles)
    except json.JSONDecodeError:
        # Логування помилки
        await callback.message.edit_text(
            "❌ Помилка при завантаженні деталей товарів у замовленні.",
            reply_markup=get_order_details_keyboard(order_id)  # Повернення до деталей з можливістю зміни статусу
        )
        await callback.answer()
        return

    items_text_list = []
    for barcode, quantity in items_dict.items():
        # ВИПРАВЛЕНО: Пошук по штрих-коду
        product_info = await product_manager_instance.get_product_info_by_barcode(barcode)
        product_name = product_info[0] if product_info else f"Штрих-код {barcode}"
        article = product_info[3] if product_info else "N/A"  # Отримуємо артикул для відображення
        items_text_list.append(f"- {product_name} (Арт: {article}, ШК: {barcode}): {quantity} шт.")

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

    if order.tracking_number:
        order_details_message += f"🔢 <b>Номер відправлення:</b> {order.tracking_number}\n"


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
    order_id = int(callback.data.split(":")[1])
    keyboard = get_change_status_keyboard(order_id)

    await callback.message.edit_text(
        f"✏️ Оберіть новий статус для замовлення #{order_id}:",
        reply_markup=keyboard
    )


@admin.callback_query(F.data.startswith("change_order_status:"))
async def change_order_status(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает изменение статуса заказа администратором.
    Если статус "Отправлено", запрашивает трекинг-номер.
    """
    try:
        _, order_id_str, new_status_value = callback.data.split(":")
        order_id = int(order_id_str)
        new_status = OrderStatus(new_status_value)

        if new_status == OrderStatus.SHIPPED:
            await state.update_data(order_id=order_id)
            await state.set_state(AdminOrderStates.EnterTrackingNumber)
            await callback.message.edit_text(
                f"Введіть номер відправлення (ТТН) для замовлення #{order_id}:",
                reply_markup=get_cancel_tracking_input_keyboard(order_id)
            )
            await callback.answer()
            return

        updated_order = await update_order_status(order_id, new_status)

        if not updated_order:
            await callback.answer("❌ Не вдалося оновити статус замовлення.", show_alert=True)
            return

        user_id = updated_order.tg_id
        status_description = OrderStatus(new_status).get_uk_description()
        notification_message = f"Статус Вашого замовлення #{order_id} змінено на: {status_description}"
        await callback.bot.send_message(chat_id=user_id, text=notification_message)

        # Оновлюємо вигляд деталей замовлення для адміна
        # Замість зміни callback.data, відтворюємо логіку show_admin_order_details
        await show_admin_order_details(callback)

    except Exception as e:
        # Уникаємо помилки MESSAGE_TOO_LONG, надсилаючи коротке повідомлення
        print(f"Error in change_order_status: {e}")  # Для логування повної помилки в консоль
        await callback.answer(f"⚠️ Відбулася помилка. Див. консоль.", show_alert=True)


@admin.callback_query(F.data.startswith("cancel_tracking_input:"))
async def cancel_tracking_input(callback: CallbackQuery, state: FSMContext):
    """
    Скасовує введення трекінг-номера, очищує стан та повертає до деталей замовлення.
    """
    await state.clear()
    await show_admin_order_details(callback)


@admin.message(AdminOrderStates.EnterTrackingNumber, F.text)
async def process_tracking_number(message: Message, state: FSMContext):
    """
    Обрабатывает ввод трекинг-номера, обновляет заказ и уведомляет пользователя.
    """
    try:
        data = await state.get_data()
        order_id = data.get("order_id")

        if not order_id:
            await message.answer("Сталася помилка стану. Будь ласка, спробуйте знову змінити статус замовлення.")
            await state.clear()
            return

        tracking_number_str = message.text.strip()
        if not tracking_number_str.isdigit():
            await message.answer("Номер відправлення повинен містити лише цифри. Спробуйте ще раз:")
            return

        tracking_number = int(tracking_number_str)

        updated_order = await update_order_status(order_id, OrderStatus.SHIPPED, tracking_number)

        if not updated_order:
            await message.answer("❌ Не вдалося оновити статус замовлення. Спробуйте знову.")
            await state.clear()
            return

        await state.clear()

        user_id = updated_order.tg_id
        status_description = OrderStatus.SHIPPED.get_uk_description()
        notification_message = (
            f"Статус Вашого замовлення #{order_id} змінено на: {status_description}.\n"
            f"🚚 Ваш номер для відстеження (ТТН): {tracking_number}"
        )
        await message.bot.send_message(chat_id=user_id, text=notification_message)

        await message.answer(f"✅ Статус замовлення #{order_id} оновлено на 'Відправлено', номер ТТН додано.")

        # Показуємо адміну оновлені деталі замовлення
        product_manager_instance = ProductManager()
        articles_dict = json.loads(updated_order.articles)
        items_text_list = []
        for article_code, quantity in articles_dict.items():
            product_info = await product_manager_instance.get_product_info(article_code)
            product_name = product_info[0] if product_info else f"Артикул {article_code}"
            items_text_list.append(f"- {product_name} (Арт: {article_code}): {quantity} шт.")
        items_text = "\n".join(items_text_list)

        order_details_message = f"📦 <b>Деталі замовлення #{updated_order.id}</b>:\n\n"
        order_details_message += f"📅 <b>Дата:</b> {updated_order.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        order_details_message += f"👤 <b>Отримувач:</b> {updated_order.name}\n"
        order_details_message += f"📞 <b>Телефон:</b> {updated_order.phone}\n\n"
        order_details_message += f"🛒 <b>Товари:</b>\n{items_text}\n\n"
        order_details_message += f"💰 <b>Сума замовлення:</b> {updated_order.total_price:.2f} грн\n"

        if updated_order.comment and updated_order.comment.strip():
            order_details_message += f"💬 <b>Коментар клієнта:</b> {updated_order.comment}\n"

        if updated_order.tracking_number:
            order_details_message += f"🔢 <b>Номер відправлення:</b> {updated_order.tracking_number}\n"

        order_details_message += f"\n💳 <b>Спосіб оплати:</b> {updated_order.payment_method}\n"
        order_details_message += f"🚚 <b>Доставка:</b> {updated_order.delivery}\n"
        order_details_message += f"📍 <b>Адреса:</b> {updated_order.address}\n"
        order_details_message += f"📌 <b>Статус:</b> {OrderStatus(updated_order.status).get_uk_description()}"

        await message.answer(
            order_details_message,
            reply_markup=get_order_details_keyboard(order_id),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"⚠️ Відбулася помилка: {str(e)}")
    finally:
        await state.clear()


@admin.callback_query(F.data == "admin_generate_deeplinks")
async def ask_for_article(callback: CallbackQuery, state: FSMContext):
    """Запитує у адміністратора артикул для генерації посилань."""
    await state.set_state(AdminOrderStates.GenerateDeeplink)
    await callback.message.edit_text(
        "Будь ласка, надішліть артикул товару, для якого потрібно згенерувати посилання.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@admin.message(AdminOrderStates.GenerateDeeplink, F.text)
async def generate_deeplinks(message: Message, state: FSMContext, bot: Bot):
    """Генерує та відправляє діплінки для зазначеного артикулу."""
    await state.clear()
    article = message.text.strip()

    product_manager = ProductManager()
    barcodes_info = await product_manager.get_barcodes_by_article(article)

    if not barcodes_info:
        await message.answer(
            f"❌ Товар з артикулом `{article}` не знайдено або для нього не вказані штрих-коди.",
            parse_mode="Markdown",
            reply_markup=get_admin_main_menu()
        )
        return

    try:
        me = await bot.get_me()
        bot_username = me.username

        deeplinks = []
        # ВИПРАВЛЕНО: Використання лічильника замість назви товару
        size_counter = 1
        for barcode, name in barcodes_info:
            link = f"https://t.me/{bot_username}?start={barcode}"
            # Формуємо рядок "Розмір 1", "Розмір 2" і т.д.
            deeplinks.append(f"Розмір {size_counter} - {link}")
            size_counter += 1

        # Формуємо повідомлення, яке легко скопіювати
        final_links_str = "\n".join(deeplinks)
        response_text = f"Посилання для артикулу `{article}`:\n\n`{final_links_str}`"


        await message.answer(
            response_text,
            parse_mode="Markdown",
            )

        await message.answer(
            "Головне меню адміністратора:",
            reply_markup=get_admin_main_menu()
        )

    except Exception as e:
        logger.error(f"Помилка під час генерації діплінків: {e}", exc_info=True)
        await message.answer("❌ Сталася помилка під час генерації посилань.")


# Обробник для кнопки "Назад" зі стану генерації
@admin.callback_query(AdminOrderStates.GenerateDeeplink, F.data == "admin_main_menu")
async def back_to_main_menu_from_deeplink(callback: CallbackQuery, state: FSMContext):
    """Обробляє повернення до головного меню зі стану генерації діплінків."""
    await state.clear()
    await callback.message.edit_text(
        "Головне меню адміністратора:"
    )
    await callback.answer()
