from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.database.models import OrderStatus


def get_admin_main_menu() -> InlineKeyboardMarkup:
    """
    Створює головне меню адміністратора.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📦 Замовлення",
        callback_data="admin_orders_menu"
    )
    # <-- Додано нову кнопку
    builder.button(
        text="🔗 Клавіатура під пост",
        callback_data="admin_generate_deeplinks"
    )
    builder.adjust(1)  # Розташовуємо кнопки у стовпчик
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


def edit_order_status() -> InlineKeyboardMarkup:
    """
    Клавіатура для зміни статусу замовлення.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️Змінити статус",
        callback_data="edit_order_status"
    )
    return builder.as_markup()


def get_order_details_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Клавіатура для перегляду деталей замовлення з кнопками "Назад" та "Змінити статус".
    """
    builder = InlineKeyboardBuilder()

    # Кнопка "Змінити статус замовлення"
    builder.button(
        text="✏️ Змінити статус замовлення",
        callback_data=f"edit_order_status:{order_id}"
    )
    # Кнопка "Назад до меню замовлень"
    builder.button(
        text="🔙 Назад до меню замовлень",
        callback_data="admin_orders_menu"
    )

    builder.adjust(1)  # Кнопки у стовпчик
    return builder.as_markup()


def get_back_to_order_info_menu() -> InlineKeyboardMarkup:
    """
    Клавіатура для повернення до інформації про ордер.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Назад до інформації про замовлення",
        callback_data="back_to_order_info_menu"
    )
    return builder.as_markup()


def get_change_status_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Створює клавіатуру для зміни статусу замовлення з усіма можливими статусами та кнопкою "Назад".

    Args:
        order_id (int): ID замовлення.

    Returns:
        InlineKeyboardMarkup: Клавіатура з кнопками для зміни статусу.
    """
    builder = InlineKeyboardBuilder()

    # Список статусів і їх описів
    statuses = [
        ("new", "🕒 В обробці"),
        ("confirmed", "✅ Підтверджено"),
        ("shipped", "🚚 Відправлено"),
        ("delivered", "📦 Доставлено"),
        ("cancelled_by_admin", "❌ Скасовано адміністратором"),
    ]

    # Додаємо кнопки для кожного статусу
    for status_value, status_text in statuses:
        builder.button(
            text=status_text,
            callback_data=f"change_order_status:{order_id}:{status_value}"
        )

    # Додаємо кнопку "Назад" для повернення до деталей замовлення
    builder.button(
        text="🔙 Назад до деталей замовлення",
        callback_data=f"admin_order_details:{order_id}"
    )

    builder.adjust(1)  # Всі кнопки у стовпчик
    return builder.as_markup()


def get_cancel_tracking_input_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Клавіатура для скасування вводу трекінг-номера та повернення до деталей замовлення.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Повернутися",
        callback_data=f"cancel_tracking_input:{order_id}"
    )
    return builder.as_markup()
