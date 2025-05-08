from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.database.models import OrderStatus


def get_admin_main_menu() -> InlineKeyboardMarkup:
    """
    Створює головне меню адміністратора з кнопкою для переходу до замовлень.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📦 Замовлення",
        callback_data="admin_orders_menu"
    )
    return builder.as_markup()


def get_orders_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Створює меню замовлень для адміністратора з кнопками для перегляду замовлень за статусом.
    """
    builder = InlineKeyboardBuilder()

    # Кнопка для всіх замовлень
    builder.button(
        text="🛒 Всі замовлення",
        callback_data="admin_all_orders"
    )

    # Кнопки для фільтрів за статусами замовлень
    statuses = [
        ("🕒 В обробці", "new"),
        ("✅ Підтверджено", "confirmed"),
        ("🚚 Відправлено", "shipped"),
        ("📦 Доставлено", "delivered"),
        ("❌ Скасовано адміністратором", "cancelled_by_admin"),
        ("❌ Скасовано користувачем", "cancelled_by_user"),
    ]

    for text, status in statuses:
        builder.button(
            text=text,
            callback_data=f"admin_orders_status:{status}"
        )

    # Кнопка "Назад" для повернення до головного меню
    builder.button(
        text="🔙 Назад",
        callback_data="admin_main_menu"
    )

    # Додаємо всі кнопки до клавіатури
    builder.adjust(1)  # Всі кнопки у стовпчик

    return builder.as_markup()


def get_orders_keyboard(orders, page, total_pages) -> InlineKeyboardMarkup:
    """
    Створює клавіатуру для відображення замовлень із пагінацією.
    """
    builder = InlineKeyboardBuilder()

    # Додаємо кнопки для кожного замовлення
    for order in orders:
        builder.button(
            text=f"#{order.id} - {OrderStatus(order.status).get_uk_description()}",
            callback_data=f"admin_order_details:{order.id}"
        )

    # Кнопки навігації
    navigation_buttons = []

    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Попередня",
                callback_data=f"admin_new_orders_page:{page - 1}"
            )
        )

    if page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="➡️ Наступна",
                callback_data=f"admin_new_orders_page:{page + 1}"
            )
        )

    if navigation_buttons:
        builder.row(*navigation_buttons)

    # Кнопка повернення до "Меню замовлень"
    builder.button(
        text="🔙 Назад",
        callback_data="admin_orders_menu"
    )

    builder.adjust(1)  # Всі кнопки у стовпчик

    return builder.as_markup()


def get_back_to_main_menu() -> InlineKeyboardMarkup:
    """
    Створює клавіатуру для повернення до головного меню адміністратора.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Назад до головного меню",
        callback_data="admin_main_menu"
    )
    return builder.as_markup()


def get_back_to_orders_menu() -> InlineKeyboardMarkup:
    """
    Клавіатура для повернення до "Меню замовлень".
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Назад до меню замовлень",
        callback_data="admin_orders_menu"
    )
    return builder.as_markup()
