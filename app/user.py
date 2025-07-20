import logging
from app.cart import *
from app.user_order import OrderManager
from app.database.requests import set_user
from app.cart import RedisCart
from app.database.products import ProductManager
from app.user_order import process_show_orders, process_orders_pagination, show_order_details
from app.user_keyboards import get_back_to_main_menu

product_manager = ProductManager()

user = Router()
cart = RedisCart()
order_manager = OrderManager(user)

logger = logging.getLogger(__name__)


@user.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """
    Обрабатывает команду /start и диплинки.
    Формат диплинка: https://t.me/bot?start=2000000048291
    где 2000000048291 - штрих-код товара.
    """
    try:
        user_id = message.from_user.id
        user_name = message.from_user.full_name
        await set_user(user_id, user_name)
        barcode = command.args

        if barcode:
            product_info = await product_manager.get_product_info_by_barcode(barcode)
            if product_info:
                name, price, available, article = product_info
                text = f"📦 {name}\nАртикул: {article}\n💰 ціна: {price:.2f} грн.\n📊 В наявносі: {available} шт.\n\n"
                text += "Щоб додати товар в кошик, натисніть кнопку нижче 👇"
                await message.answer(text, reply_markup=get_product_keyboard(barcode, in_cart=False))
                return

        await message.answer(
            f"👋 Ласкаво просимо!\nОберіть необхідний розділ",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Помилка в cmd_start: {e}", exc_info=True)
        await message.answer("Виникла помилка.")


@user.message(F.text)
async def handle_barcode(message: Message):
    try:
        barcode = message.text.strip()
        product_info = await product_manager.get_product_info_by_barcode(barcode)

        if product_info is None:
            await message.answer("❌ Товару з таким штрихкодом не знайдено.")
            return

        name, price, available, article = product_info
        response = f"📦 {name}\nАртикул: {article}\nШтрих-код: {barcode}\n💰 Цена: {price:.2f} грн.\n📊 В наличии: {available} шт."
        await message.answer(response, reply_markup=get_product_keyboard(barcode, in_cart=False))
    except Exception as e:
        await message.answer("❌ Помилка при обробці запиту.")
        print(f"Помилка в handle_barcode: {e}")


# Обработчики callback-запросов для главного меню
@user.callback_query(F.data == "show_catalog")
async def process_show_catalog(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗂 Каталог товарів\n\nОберіть категорію:",
        reply_markup=get_catalog_keyboard()
    )


@user.callback_query(F.data == "show_support")
async def process_show_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "💬 Підтримка\n\n"
        "Оберіть опцію нижче або напишіть повідомлення користувачу (буде додано посилання на користувача):",
        reply_markup=get_support_keyboard()
    )


@user.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        f"👋 Головне меню\n\n"
        f"Вас вітає магазин \"Твій Стиль\"\n\n"
        f"Оберіть потрібний розділ:",
        reply_markup=get_main_keyboard()
    )


@user.message(F.text)
async def handle_article(message: Message):
    try:
        article = message.text.strip()

        product_details = await product_manager.get_product_details(article)

        if product_details is None:
            await message.answer("❌ Товару з таким артикулом не знайдено.")
            return

        # Формуємо відповідь
        name = product_details["name"]
        article = product_details["article"]
        price = product_details["price"]
        specifications = product_details["specifications"]

        response = f"📦 {name}\nАртикул: {article}\n💰 Ціна: {price:.2f} грн.\n\n"

        if len(specifications) > 1:
            response += "🗂 Розміри/кольори:\n"
            for spec in specifications:
                response += f"🔘 {spec['specification']}\n📊 В наявності: {spec['quantity']} шт.\n\n"
        else:
            spec = specifications[0]
            response += f"📊 В наявності: {spec['quantity']} шт.\n"

        await message.answer(response)

    except Exception as e:
        await message.answer("❌ Виникла помилка під час обробки запиту. Спробуйте пізніше.")
        print(f"Помилка у handle_article: {e}")


@user.callback_query(F.data.startswith("add_to_cart_"))
async def process_add_to_cart(callback: CallbackQuery):
    try:
        barcode = callback.data.replace("add_to_cart_", "")
        product_info = await product_manager.get_product_info_by_barcode(barcode)
        if not product_info:
            await callback.answer("❌ Товар не знайдено", show_alert=True)
            return

        name, price, available, article = product_info
        if available <= 0:
            await callback.answer("❌ Товар тимчасово відсутній", show_alert=True)
            return

        current_cart = await cart.get_cart(callback.from_user.id)
        current_quantity = current_cart.get(barcode, 0) if current_cart else 0

        if current_quantity >= available:
            await callback.answer(f"❌ К кошику максимальна кількість товару ({available} шт.)", show_alert=True)
            return
        if current_quantity >= 999:
            await callback.answer("❌ Не можна додати більше 999 одиниць товару", show_alert=True)
            return

        success, msg = await cart.add_item_to_cart(callback.from_user.id, barcode)
        if success:
            text = f"📦 {name}\nАртикул: {article}\n💰 Ціна: {price:.2f} грн.\n📊 В наявності: {available} шт.\n\n✅ Товар додано в кошик!"
            updated_cart = await cart.get_cart(callback.from_user.id)
            item_quantity = updated_cart.get(barcode, 0)
            if item_quantity > 0:
                text += f"\n🛒 В кошику: {item_quantity} шт."
            await callback.message.edit_text(text, reply_markup=get_product_keyboard(barcode, True))
            await callback.answer("✅ Товар додано в кошик!")
        else:
            await callback.answer("❌ Помилка при додаванні товару.", show_alert=True)
    except Exception as e:
        print(f"Error adding product to cart: {e}")
        await callback.answer("❌ Виникла помилка.", show_alert=True)


# Обработчик для просмотра корзины через главное меню
@user.callback_query(F.data == "show_cart")
async def process_show_cart(callback: CallbackQuery):
    """Показывает содержимое корзины"""
    try:
        # Инициализируем подключение к Redis
        await cart.ensure_connection()

        # Получаем корзину пользователя
        user_cart = await cart.get_cart(callback.from_user.id)

        if not user_cart:
            await callback.message.edit_text(
                "🛒 Ваш кошик порожній\n\n"
                "Щоб додати товари, перейдіть до каталогу 📋",
                reply_markup=get_cart_keyboard(has_items=False)  # Передаем False для пустой корзины
            )
            return

        # Формируем детальную информацию о товарах в корзине
        cart_text = await format_cart_content(user_cart, callback.from_user.id)

        # Обновляем сообщение с корзиной
        await callback.message.edit_text(
            cart_text,
            reply_markup=get_cart_keyboard(has_items=True)  # Передаем True для непустой корзины
        )

    except Exception as e:
        logger.error(f"Error showing cart: {e}")
        await callback.message.edit_text(
            "❌ Виникла помилка при завантаженні кошика.\n"
            "Спробуйте пізніше або зверніться до підтримки.",
            reply_markup=get_back_to_main_menu()  # Всегда даем возможность вернуться в главное меню
        )
        await callback.answer("Помилка при завантаженні кошика")


# Обработчик возврата в главное меню
@user.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: CallbackQuery):
    """Возвращает пользователя в главное меню"""
    await callback.message.edit_text(
        "🏠 Головне меню\n\n"
        "Оберіть потрібний розділ:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


# Обработчик очистки корзины с возможностью возврата в главное меню
@user.callback_query(F.data == "clear_cart")
async def process_clear_cart(callback: CallbackQuery):
    try:
        success, msg = await cart.clear_cart(callback.from_user.id)

        if success:
            await callback.message.edit_text(
                "🛒 Кошик очищено\n\n"
                "Щоб додати товари, перейдіть до каталогу 📋",
                reply_markup=get_cart_keyboard(has_items=False)  # Показываем клавиатуру для пустой корзины
            )
            await callback.answer("✅ Кошик очищено")
        else:
            await callback.answer("❌ Помилка при очищенні кошика")

    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        await callback.message.edit_text(
            "❌ Виникла помилка при очищенні кошика.\n"
            "Спробуйте пізніше або зверніться до підтримки.",
            reply_markup=get_back_to_main_menu()  # Даем возможность вернуться в главное меню
        )
        await callback.answer("❌ Помилка при очищенні кошика")


@user.callback_query(F.data.startswith("increase_"))
async def process_increase_quantity(callback: CallbackQuery):
    article = callback.data.replace("increase_", "")

    try:
        user_cart = await cart.get_cart(callback.from_user.id)
        if not user_cart or article not in user_cart:
            await callback.answer("❌ Товар не знайдено в кошику")
            return

        current_quantity = user_cart[article]
        product_info = await product_manager.get_product_info(article)

        if not product_info:
            await callback.answer("❌ Товар недоступний")
            return

        name, price, available = product_info

        if current_quantity >= available:
            await callback.answer(
                f"❌ Неможливо додати більше. Доступно: {available} шт.",
                show_alert=True
            )
            return

        if current_quantity >= 10:
            await callback.answer(
                "❌ Не можна додати більше 10 одиниць товару",
                show_alert=True
            )
            return

        # Увеличиваем количество
        success, msg = await cart.update_quantity(
            callback.from_user.id,
            article,
            current_quantity + 1
        )

        if success:
            # Обновляем отображение корзины
            user_cart = await cart.get_cart(callback.from_user.id)
            cart_text = await format_cart_content(user_cart, callback.from_user.id)

            await callback.message.edit_text(
                cart_text,
                reply_markup=get_cart_keyboard(True)
            )
            await callback.answer("✅ Кількість збільшено")
        else:
            await callback.answer("❌ Помилка при оновленні кількості")

    except Exception as e:
        logger.error(f"Error increasing quantity: {e}")
        await callback.answer("❌ Помилка при оновленні кількості")


# Обработчик уменьшения количества товара
@user.callback_query(F.data.startswith("decrease_"))
async def process_decrease_quantity(callback: CallbackQuery):
    article = callback.data.replace("decrease_", "")

    try:
        user_cart = await cart.get_cart(callback.from_user.id)
        if not user_cart or article not in user_cart:
            await callback.answer("❌ Товар не знайдено в кошику")
            return

        current_quantity = user_cart[article]

        if current_quantity <= 1:
            # Если количество 1 или меньше, удаляем товар
            success, msg = await cart.remove_item(callback.from_user.id, article)
        else:
            # Уменьшаем количество
            success, msg = await cart.update_quantity(
                callback.from_user.id,
                article,
                current_quantity - 1
            )

        if success:
            # Обновляем отображение корзины
            user_cart = await cart.get_cart(callback.from_user.id)
            if not user_cart:  # Если корзина пуста после удаления
                await callback.message.edit_text(
                    "🛒 Ваш кошик порожній\n\n"
                    "Щоб додати товари, перейдіть до каталогу 📋",
                    reply_markup=get_main_keyboard()
                )
            else:
                cart_text = await format_cart_content(user_cart, callback.from_user.id)
                await callback.message.edit_text(
                    cart_text,
                    reply_markup=get_cart_keyboard(True)
                )
            await callback.answer("✅ Кількість зменшено")
        else:
            await callback.answer("❌ Помилка при оновленні кількості")

    except Exception as e:
        logger.error(f"Error decreasing quantity: {e}")
        await callback.answer("❌ Помилка при оновленні кількості")


# Обработчик очистки корзины
@user.callback_query(F.data == "clear_cart")
async def process_clear_cart(callback: CallbackQuery):
    try:
        success, msg = await cart.clear_cart(callback.from_user.id)

        if success:
            await callback.message.edit_text(
                "🛒 Кошик очищено\n\n"
                "Щоб додати товари, перейдіть до каталогу 📋",
                reply_markup=get_main_keyboard()
            )
            await callback.answer("✅ Кошик очищено")
        else:
            await callback.answer("❌ Помилка при очищенні кошика")

    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        await callback.answer("❌ Помилка при очищенні кошика")


@user.callback_query(F.data.startswith("remove_from_cart_"))
async def process_remove_from_cart(callback: CallbackQuery):
    try:
        barcode = callback.data.replace("remove_from_cart_", "")
        success, msg = await cart.remove_item(callback.from_user.id, barcode)
        if success:
            # Обновляем сообщение, чтобы показать, что товар удален
            product_info = await product_manager.get_product_info_by_barcode(barcode)
            if product_info:
                name, price, available, article = product_info
                text = f"📦 {name}\nАртикул: {article}\n💰 Цена: {price:.2f} грн.\n📊 В наличии: {available} шт.\n\n✅ Товар удален из корзины!"
                await callback.message.edit_text(text, reply_markup=get_product_keyboard(barcode, False))
            await callback.answer("✅ Товар удален из корзины")
        else:
            await callback.answer("❌ Ошибка при удалении товара", show_alert=True)
    except Exception as e:
        logger.error(f"Error removing item from cart: {e}")
        await callback.answer("❌ Ошибка при удалении товара.", show_alert=True)


@user.callback_query(F.data == "delete_items")
async def show_delete_items_menu(callback: CallbackQuery):
    """Показує меню для видалення окремих товарів."""
    try:
        user_cart = await cart.get_cart(callback.from_user.id)
        if not user_cart:
            await callback.answer("Кошик порожній", show_alert=True)
            return

        items_list = []
        for barcode, _ in user_cart.items():
            product_info = await product_manager.get_product_info_by_barcode(barcode)
            if product_info:
                name, _, _, _ = product_info
                items_list.append((barcode, name))

        await callback.message.edit_text(
            "🗑 Виберіть товар для видалення:",
            reply_markup=get_delete_items_keyboard(items_list)
        )
    except Exception as e:
        logger.error(f"Error showing delete items menu: {e}")
        await callback.answer("Помилка при завантаженні меню видалення", show_alert=True)


# Обработчик для удаления конкретного товара
@user.callback_query(F.data.startswith("delete_item_"))
async def delete_specific_item(callback: CallbackQuery):
    """Удаляет выбранный товар из корзины"""
    try:
        article = callback.data.replace("delete_item_", "")
        success, msg = await cart.remove_item(callback.from_user.id, article)

        if success:
            # Получаем обновленную корзину
            user_cart = await cart.get_cart(callback.from_user.id)

            if not user_cart:
                # Если корзина пуста после удаления
                await callback.message.edit_text(
                    "🛒 Ваш кошик порожній\n\n"
                    "Щоб додати товари, перейдіть до каталогу 📋",
                    reply_markup=get_cart_keyboard(has_items=False)
                )
            else:
                # Если в корзине остались товары, показываем обновленный список для удаления
                text = "🗑 Виберіть товар для видалення:\n\n"
                items_list = []

                for cart_article, quantity in user_cart.items():
                    product_info = await product_manager.get_product_info(cart_article)
                    if product_info:
                        name, price, _ = product_info
                        text += (
                            f"📦 {name}\n"
                            f"Артикул: {cart_article}\n"
                            f"Кількість: {quantity} шт.\n"
                            f"Ціна: {price:.2f} грн. x {quantity} = {price * quantity:.2f} грн.\n"
                            "➖➖➖➖➖➖➖➖➖➖\n\n"
                        )
                        items_list.append((cart_article, name))

                text += "Натисніть на товар, який хочете видалити:"

                await callback.message.edit_text(
                    text,
                    reply_markup=get_delete_items_keyboard(items_list)
                )

            await callback.answer("✅ Товар видалено з кошика")
        else:
            await callback.answer(
                "❌ Помилка при видаленні товару",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Error deleting specific item: {e}")
        await callback.answer(
            "❌ Помилка при видаленні товару",
            show_alert=True
        )


# Обработчик возврата к просмотру корзины
@user.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: CallbackQuery):
    """Повертає до перегляду кошика."""
    await process_show_cart(callback)


@user.callback_query(F.data == "change_quantities")
async def show_quantity_change_menu(callback: CallbackQuery):
    """Показує меню зміни кількості товарів."""
    user_cart = await cart.get_cart(callback.from_user.id)
    if not user_cart:
        await callback.answer("Кошик порожній", show_alert=True)
        return
    await update_quantity_menu(callback)


async def update_quantity_menu(callback: CallbackQuery, success_message: str = None):
    """Допоміжна функція для оновлення меню зміни кількості."""
    try:
        user_cart = await cart.get_cart(callback.from_user.id)
        if not user_cart:
            # Якщо кошик спорожнів, повертаємо до головного меню кошика
            await process_show_cart(callback)
            return

        items_info = []
        for barcode, quantity in user_cart.items():
            product_info = await product_manager.get_product_info_by_barcode(barcode)
            if product_info:
                name, _, available, _ = product_info
                items_info.append({
                    'barcode': barcode,
                    'name': name,
                    'quantity': quantity,
                    'available': available
                })

        await callback.message.edit_text(
            "📝 Зміна кількості товарів:",
            reply_markup=get_quantity_change_keyboard(items_info)
        )
        if success_message:
            await callback.answer(success_message)
    except Exception as e:
        logger.error(f"Error updating quantity menu: {e}")
        await callback.answer("❌ Помилка при оновленні меню")


@user.callback_query(F.data.startswith("qty_increase_"))
async def quantity_increase(callback: CallbackQuery):
    """Збільшує кількість товару."""
    barcode = callback.data.replace("qty_increase_", "")
    user_cart = await cart.get_cart(callback.from_user.id)
    current_quantity = user_cart.get(barcode, 0)

    product_info = await product_manager.get_product_info_by_barcode(barcode)
    if not product_info:
        await callback.answer("Товар більше недоступний", show_alert=True)
        return

    _, _, available, _ = product_info

    if current_quantity >= available:
        await callback.answer(f"Більше додати неможливо. Доступно: {available} шт.", show_alert=True)
        return

    success, _ = await cart.update_item_quantity(callback.from_user.id, barcode, current_quantity + 1)
    if success:
        await update_quantity_menu(callback, "✅ Кількість збільшено")


@user.callback_query(F.data.startswith("qty_decrease_"))
async def quantity_decrease(callback: CallbackQuery):
    """Зменшує кількість товару."""
    barcode = callback.data.replace("qty_decrease_", "")
    user_cart = await cart.get_cart(callback.from_user.id)
    current_quantity = user_cart.get(barcode, 0)

    if current_quantity <= 1:
        await callback.answer("Для видалення товару використовуйте меню видалення.", show_alert=True)
        return

    success, _ = await cart.update_item_quantity(callback.from_user.id, barcode, current_quantity - 1)
    if success:
        await update_quantity_menu(callback, "✅ Кількість зменшено")


@user.callback_query(F.data == "quantity_info")
async def show_quantity_info(callback: CallbackQuery):
    """Показывает информацию о количестве товара"""
    await callback.answer(
        "Поточна кількість / Доступно на складі",
        show_alert=True
    )


# Обработчик для отображения заказов
@user.callback_query(F.data == "show_orders")
async def handle_show_orders(callback: CallbackQuery):
    await process_show_orders(callback)


# Обработчик для навигации по страницам заказов
@user.callback_query(F.data.startswith("orders_page:"))
async def handle_orders_pagination(callback: CallbackQuery):
    await process_orders_pagination(callback)


# Реєструємо обробник
@user.callback_query(F.data.startswith("order_details:"))
async def handle_order_details(callback: CallbackQuery):
    await show_order_details(callback)
