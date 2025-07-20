from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Tuple
from app.database.models import OrderStatus


def get_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создает главную клавиатуру бота с основными кнопками:
    - Каталог
    - Корзина
    - Мої замовлення
    - Підтримка
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки в Builder
    #builder.button(text="🗂 Каталог", callback_data="show_catalog")
    builder.button(text="🛒 Кошик", callback_data="show_cart")
    builder.button(text="📦 Мої замовлення", callback_data="show_orders")
    builder.button(text="💬 Підтримка", callback_data="show_support")

    # Устанавливаем расположение кнопок (2 в ряд)
    builder.adjust(2)

    return builder.as_markup()


def get_back_to_main_menu() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой возврата в главное меню"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏠 Повернутися до головного меню",
        callback_data="back_to_main"
    )

    return builder.as_markup()


def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для каталога"""
    builder = InlineKeyboardBuilder()

    # Здесь можно добавить категории товаров
    builder.button(text="👕 Одяг", callback_data="category_clothes")
    builder.button(text="👞 Взуття", callback_data="category_shoes")
    builder.button(text="👜 Аксесуари", callback_data="category_accessories")

    # Кнопка возврата в главное меню
    builder.button(text="◀️ Головне меню", callback_data="back_to_main")

    # 2 кнопки в ряд для категорий, последняя кнопка отдельно
    builder.adjust(2, 2, 1)

    return builder.as_markup()


def get_cart_keyboard(has_items: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_items:
        builder.button(text="💳 Оформити замовлення", callback_data="checkout")
        builder.button(text="📝 Змінити кількість", callback_data="change_quantities")
        builder.button(text="✂️ Видалити товари", callback_data="delete_items")
        builder.button(text="🗑 Очистити кошик", callback_data="clear_cart")
    #builder.button(text="📋 Перейти до каталогу", callback_data="show_catalog")
    builder.button(text="🏠 Головне меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_product_keyboard(barcode: str, in_cart: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для товара.
    Args:
        barcode (str): Штрих-код товара.
        in_cart (bool): Есть ли товар в корзине.
    """
    builder = InlineKeyboardBuilder()
    if in_cart:
        builder.button(
            text="🗑 Видалити з кошика",
            callback_data=f"remove_from_cart_{barcode}"
        )
        builder.button(text="🛒 Переглянути кошик", callback_data="show_cart")
    else:
        builder.button(
            text="🛒 Додати до кошика",
            callback_data=f"add_to_cart_{barcode}"
        )
    #builder.button(text="📋 До каталогу", callback_data="show_catalog")
    builder.button(text="🏠 Головне меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_order_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для просмотра заказа"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📋 Деталі замовлення", callback_data=f"order_details_{order_id}")
    builder.button(text="❌ Скасувати замовлення", callback_data=f"cancel_order_{order_id}")
    builder.button(text="◀️ До списку замовлень", callback_data="show_orders")
    builder.button(text="◀️ Головне меню", callback_data="back_to_main")

    # Кнопки в один ряд
    builder.adjust(1)

    return builder.as_markup()


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для раздела поддержки"""
    builder = InlineKeyboardBuilder()

    builder.button(text="❓ Часті питання", callback_data="faq")
    builder.button(text="◀️ Головне меню", callback_data="back_to_main")

    # Кнопки в один ряд
    builder.adjust(1)

    return builder.as_markup()


def get_delete_items_keyboard(items: List[Tuple[str, str]]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для удаления отдельных товаров.
    Args:
        items: Список кортежей (штрих-код, название) товаров в корзине.
    """
    builder = InlineKeyboardBuilder()
    for barcode, name in items:
        short_name = name[:30] + "..." if len(name) > 30 else name
        builder.button(
            text=f"❌ {short_name}",
            callback_data=f"delete_item_{barcode}"
        )
    builder.button(text="🔙 Назад до кошика", callback_data="back_to_cart")
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_cart_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой возврата к корзине"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔙 Назад до кошика",
        callback_data="back_to_cart"
    )

    return builder.as_markup()


def get_quantity_change_keyboard(items_info: List[dict]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для изменения количества товаров.
    Args:
        items_info: Список словарей с информацией о товарах (включая barcode).
    """
    keyboard = []
    for item in items_info:
        name_row = [InlineKeyboardButton(text=f"📦 {item['name'][:30]}...", callback_data=f"qinfo_{item['barcode']}")]
        quantity_row = [
            InlineKeyboardButton(text="➖", callback_data=f"qty_decrease_{item['barcode']}"),
            InlineKeyboardButton(text=f"{item['quantity']}/{item['available']}", callback_data="quantity_info"),
            InlineKeyboardButton(text="➕", callback_data=f"qty_increase_{item['barcode']}")
        ]
        keyboard.append(name_row)
        keyboard.append(quantity_row)
    back_row = [InlineKeyboardButton(text="🔙 Назад до кошика", callback_data="back_to_cart")]
    keyboard.append(back_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_orders_keyboard(orders, page, total_pages):
    """
    Створює клавіатуру для списку замовлень із кнопками навігації.

    Args:
        orders (List[Order]): Список замовлень
        page (int): Поточна сторінка
        total_pages (int): Загальна кількість сторінок

    Returns:
        InlineKeyboardMarkup: Клавіатура
    """
    builder = InlineKeyboardBuilder()

    # Додаємо кнопки замовлень у стовпчик
    for order in orders:
        status_uk = OrderStatus(order.status).get_uk_description()  # Перекладаємо статус
        builder.button(
            text=f"Замовлення #{order.id} - {status_uk}",
            callback_data=f"order_details:{order.id}"
        )

    # Кнопки навігації (в один рядок)
    navigation_buttons = []

    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Попередня",
                callback_data=f"orders_page:{page - 1}"
            )
        )

    if page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="➡️ Наступна",
                callback_data=f"orders_page:{page + 1}"
            )
        )

    # Додаємо кнопки навігації, якщо вони є
    if navigation_buttons:
        builder.row(*navigation_buttons)

    # Кнопка повернення до головного меню (в окремому рядку)
    builder.button(
        text="🏠 Головне меню",
        callback_data="back_to_main"
    )

    builder.adjust(1)  # Всі кнопки замовлень у стовпчик
    return builder.as_markup()


def get_back_to_main_menu() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата в главное меню.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🏠 Повернутися до головного меню",
        callback_data="back_to_main"
    )
    return builder.as_markup()


def get_back_to_orders_menu() -> InlineKeyboardMarkup:
    """
    Створює клавіатуру з кнопкою повернення до меню замовлень.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Назад",
        callback_data="show_orders"
    )
    return builder.as_markup()
