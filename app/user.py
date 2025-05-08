from app.cart import *
from app.user_order import OrderManager
from app.database.requests import set_user
from app.cart import RedisCart
from app.database.products import ProductManager
from app.user_order import process_show_orders, process_orders_pagination
import logging

product_manager = ProductManager("Залишки номенклатури.xlsx")

user = Router()
cart = RedisCart()
order_manager = OrderManager(user)

logger = logging.getLogger(__name__)


@user.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """
    Обрабатывает команду /start и deep links
    Формат deep link: https://t.me/bot?start=00-00351422
    где 00-00351422 - артикул товара
    """
    try:
        # Получаем или создаем пользователя
        user_id = message.from_user.id
        user_name = message.from_user.full_name  # Получаем полное имя пользователя

        logger.info(f"Processing /start command for user {user_id} ({user_name})")

        # Создаем или получаем пользователя
        await set_user(user_id, user_name)
        logger.debug(f"User {user_id} registered in database")

        # Получаем параметр из команды start
        article = command.args

        if article:
            # Если есть артикул, показываем информацию о товаре
            product_info = product_manager.get_product_info(article)
            if product_info:
                name, price, available = product_info

                # Проверяем, есть ли товар в корзине
                user_cart = await cart.get_cart(message.from_user.id)
                in_cart = user_cart and article in user_cart

                # Формируем сообщение с информацией о товаре
                text = (
                    f"📦 {name}\n"
                    f"Артикул: {article}\n"
                    f"💰 Ціна: {price:.2f} грн.\n"
                    f"📊 В наявності: {available} шт.\n\n"
                    f"Щоб додати товар до кошика, натисніть кнопку нижче 👇"
                )

                await message.answer(
                    text,
                    reply_markup=get_product_keyboard(article, in_cart)
                )
                return

        # Если артикула нет или он не найден, показываем главное меню
        await message.answer(
            f"👋 Вітаємо у нашому магазині!\n\n"
            f"🆔 Ваш ID: {message.from_user.id}\n\n"
            f"Оберіть потрібний розділ:",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error processing /start command: {str(e)}", exc_info=True)
        await message.answer(
            "Виникла помилка при реєстрації. Будь ласка, спробуйте ще раз або зверніться до підтримки."
        )


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
        "Оберіть опцію нижче або напишіть ваше повідомлення:",
        reply_markup=get_support_keyboard()
    )


@user.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        f"👋 Головне меню\n\n"
        f"🆔 Ваш ID: {callback.from_user.id}\n\n"
        f"Оберіть потрібний розділ:",
        reply_markup=get_main_keyboard()
    )


@user.message(F.text)
async def handle_article(message: Message):
    try:
        article = message.text.strip()  # Убираем лишние пробелы

        product_info = product_manager.get_product_info(article)

        if product_info is None:
            await message.answer("❌ Товару з таким артикулом не знайдено.")
            return

        name, price, quantity = product_info

        response = (
            f"📦 Товар: {name}\n"
            f"💵 Ціна: {price:.2f} грн.\n"
            f"📊 В наявності: {quantity} шт."
        )

        await message.answer(response)
    except Exception as e:
        await message.answer("❌ Виникла помилка про пошуку товару. Спробуйте пізніше.")
        # Логирование ошибки
        print(f"Error in handle_article: {e}")


@user.callback_query(F.data.startswith("add_to_cart_"))
async def process_add_to_cart(callback: CallbackQuery):
    """
    Обработчик добавления товара в корзину
    callback.data format: add_to_cart_00-00351422 (артикул товара)
    """
    try:
        # Получаем артикул товара из callback data
        article = callback.data.replace("add_to_cart_", "")

        # Получаем информацию о товаре
        product_info = product_manager.get_product_info(article)
        if not product_info:
            await callback.answer("❌ Товар не знайдено", show_alert=True)
            return

        name, price, available = product_info

        # Проверяем наличие товара на складе
        if available <= 0:
            await callback.answer("❌ Товар тимчасово відсутній", show_alert=True)
            return

        # Проверяем текущую корзину пользователя
        current_cart = await cart.get_cart(callback.from_user.id)
        current_quantity = current_cart.get(article, 0) if current_cart else 0

        # Проверяем, не превышает ли количество доступное на складе
        if current_quantity >= available:
            await callback.answer(
                f"❌ У кошику вже максимальна кількість цього товару ({available} шт.)",
                show_alert=True
            )
            return

        # Проверяем лимит на количество одного товара
        if current_quantity >= 10:
            await callback.answer(
                "❌ Не можна додати більше 10 одиниць одного товару",
                show_alert=True
            )
            return

        # Добавляем товар в корзину
        success, msg = await cart.add_to_cart(callback.from_user.id, article)

        if success:
            # Обновляем сообщение с информацией о товаре
            text = (
                f"📦 {name}\n"
                f"Артикул: {article}\n"
                f"💰 Ціна: {price:.2f} грн.\n"
                f"📊 В наявності: {available} шт.\n\n"
                f"✅ Товар додано до кошика!"
            )

            # Получаем обновленную корзину для проверки
            updated_cart = await cart.get_cart(callback.from_user.id)
            item_quantity = updated_cart.get(article, 0) if updated_cart else 0

            # Добавляем информацию о количестве в корзине
            if item_quantity > 0:
                text += f"\n🛒 У кошику: {item_quantity} шт."

            # Обновляем клавиатуру и сообщение
            await callback.message.edit_text(
                text,
                reply_markup=get_product_keyboard(article, True)
            )

            # Показываем уведомление
            await callback.answer("✅ Товар додано до кошика!")
        else:
            # Если произошла ошибка при добавлении
            await callback.answer(
                "❌ Помилка при додаванні товару. Спробуйте пізніше.",
                show_alert=True
            )

    except Exception as e:
        print(f"Error adding product to cart: {e}")
        await callback.answer(
            "❌ Сталася помилка. Спробуйте пізніше.",
            show_alert=True
        )


# Обработчик для просмотра корзины
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
        product_info = product_manager.get_product_info(article)

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
    """Обработчик удаления товара из корзины"""
    try:
        # Получаем артикул товара из callback data
        article = callback.data.replace("remove_from_cart_", "")

        # Пробуем удалить товар из корзины
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
                # Если в корзине остались товары, обновляем её отображение
                cart_text = await format_cart_content(user_cart, callback.from_user.id)
                await callback.message.edit_text(
                    cart_text,
                    reply_markup=get_cart_keyboard(has_items=True)
                )

            # Показываем уведомление об успешном удалении
            await callback.answer("✅ Товар видалено з кошика")
        else:
            # Если произошла ошибка при удалении
            await callback.answer(
                "❌ Помилка при видаленні товару",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Error removing item from cart: {e}")
        await callback.answer(
            "❌ Помилка при видаленні товару. Спробуйте пізніше.",
            show_alert=True
        )


@user.callback_query(F.data == "delete_items")
async def show_delete_items_menu(callback: CallbackQuery):
    """Показывает меню для удаления отдельных товаров"""
    try:
        user_cart = await cart.get_cart(callback.from_user.id)

        if not user_cart:
            await callback.answer("Кошик порожній", show_alert=True)
            return

        text = "🗑 Виберіть товар для видалення:\n\n"
        items_list = []

        for article, quantity in user_cart.items():
            product_info = product_manager.get_product_info(article)
            if product_info:
                name, price, _ = product_info
                text += (
                    f"📦 {name}\n"
                    f"Артикул: {article}\n"
                    f"Кількість: {quantity} шт.\n"
                    f"Ціна: {price:.2f} грн. x {quantity} = {price * quantity:.2f} грн.\n"
                    "➖➖➖➖➖➖➖➖➖➖\n\n"
                )
                items_list.append((article, name))

        text += "Натисніть на товар, який хочете видалити:"

        # Создаем клавиатуру с товарами для удаления
        await callback.message.edit_text(
            text,
            reply_markup=get_delete_items_keyboard(items_list)
        )

    except Exception as e:
        logger.error(f"Error showing delete items menu: {e}")
        await callback.answer(
            "Помилка при завантаженні меню видалення",
            show_alert=True
        )


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
                    product_info = product_manager.get_product_info(cart_article)
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
    """Возвращает к просмотру корзины"""
    try:
        user_cart = await cart.get_cart(callback.from_user.id)

        if not user_cart:
            await callback.message.edit_text(
                "🛒 Ваш кошик порожній\n\n"
                "Щоб додати товари, перейдіть до каталогу 📋",
                reply_markup=get_cart_keyboard(has_items=False)
            )
            return

        cart_text = await format_cart_content(user_cart, callback.from_user.id)
        await callback.message.edit_text(
            cart_text,
            reply_markup=get_cart_keyboard(has_items=True)
        )

    except Exception as e:
        logger.error(f"Error returning to cart: {e}")
        await callback.answer(
            "❌ Помилка при поверненні до кошика",
            show_alert=True
        )


@user.callback_query(F.data == "change_quantities")
async def show_quantity_change_menu(callback: CallbackQuery):
    """Показывает меню изменения количества товаров"""
    try:
        user_cart = await cart.get_cart(callback.from_user.id)

        if not user_cart:
            await callback.answer("Кошик порожній", show_alert=True)
            return

        text = "📝 Зміна кількості товарів:\n\n"
        items_info = []

        for article, quantity in user_cart.items():
            product_info = product_manager.get_product_info(article)
            if product_info:
                name, price, available = product_info
                text += (
                    f"📦 {name}\n"
                    f"Артикул: {article}\n"
                    f"Поточна кількість: {quantity} шт.\n"
                    f"Доступно на складі: {available} шт.\n"
                    f"Ціна: {price:.2f} грн. x {quantity} = {price * quantity:.2f} грн.\n"
                    "➖➖➖➖➖➖➖➖➖➖\n\n"
                )
                items_info.append({
                    'article': article,
                    'name': name,
                    'quantity': quantity,
                    'available': available
                })

        text += "Використовуйте кнопки ➕ та ➖ для зміни кількості:"

        await callback.message.edit_text(
            text,
            reply_markup=get_quantity_change_keyboard(items_info)
        )

    except Exception as e:
        logger.error(f"Error showing quantity change menu: {e}")
        await callback.answer(
            "Помилка при завантаженні меню зміни кількості",
            show_alert=True
        )


async def update_quantity_menu(callback: CallbackQuery, user_cart: dict, success_message: str):
    """
    Вспомогательная функция для обновления меню изменения количества

    Args:
        callback (CallbackQuery): Callback запрос
        user_cart (dict): Корзина пользователя
        success_message (str): Сообщение об успешном обновлении
    """
    items_info = []
    text = "📝 Зміна кількості товарів:\n\n"

    for article, quantity in user_cart.items():
        product_info = product_manager.get_product_info(article)
        if product_info:
            name, price, available = product_info
            text += (
                f"📦 {name}\n"
                f"Артикул: {article}\n"
                f"Поточна кількість: {quantity} шт.\n"
                f"Доступно на складі: {available} шт.\n"
                f"Ціна: {price:.2f} грн. x {quantity} = {price * quantity:.2f} грн.\n"
                "➖➖➖➖➖➖➖➖➖➖\n\n"
            )
            items_info.append({
                'article': article,
                'name': name,
                'quantity': quantity,
                'available': available
            })

    text += "Використовуйте кнопки ➕ та ➖ для зміни кількості:"

    try:
        # Обновляем сообщение с сохранением текущего меню
        await callback.message.edit_text(
            text,
            reply_markup=get_quantity_change_keyboard(items_info)
        )
        await callback.answer(success_message)
    except Exception as e:
        logger.error(f"Error updating quantity menu: {e}")
        await callback.answer("❌ Помилка при оновленні меню")


@user.callback_query(F.data.startswith("qty_increase_"))
async def quantity_increase(callback: CallbackQuery):
    """Увеличивает количество товара в меню изменения количества"""
    try:
        article = callback.data.replace("qty_increase_", "")
        user_cart = await cart.get_cart(callback.from_user.id)

        if not user_cart or article not in user_cart:
            await callback.answer("Товар не знайдено в кошику", show_alert=True)
            return

        current_quantity = user_cart[article]
        product_info = product_manager.get_product_info(article)

        if not product_info:
            await callback.answer("Товар недоступний", show_alert=True)
            return

        name, price, available = product_info

        # Проверяем ограничения
        if current_quantity >= available:
            await callback.answer(
                f"Неможливо додати більше. Доступно: {available} шт.",
                show_alert=True
            )
            return

        if current_quantity >= 10:
            await callback.answer(
                "Не можна додати більше 10 одиниць товару",
                show_alert=True
            )
            return

        # Увеличиваем количество
        new_quantity = current_quantity + 1
        success, msg = await cart.update_quantity(
            callback.from_user.id,
            article,
            new_quantity
        )

        if success:
            # Обновляем меню изменения количества
            items_info = []
            text = "📝 Зміна кількості товарів:\n\n"

            updated_cart = await cart.get_cart(callback.from_user.id)
            for cart_article, quantity in updated_cart.items():
                product_info = product_manager.get_product_info(cart_article)
                if product_info:
                    name, price, available = product_info
                    text += (
                        f"📦 {name}\n"
                        f"Артикул: {cart_article}\n"
                        f"Поточна кількість: {quantity} шт.\n"
                        f"Доступно на складі: {available} шт.\n"
                        f"Ціна: {price:.2f} грн. x {quantity} = {price * quantity:.2f} грн.\n"
                        "➖➖➖➖➖➖➖➖➖➖\n\n"
                    )
                    items_info.append({
                        'article': cart_article,
                        'name': name,
                        'quantity': quantity,
                        'available': available
                    })

            text += "Використовуйте кнопки ➕ та ➖ для зміни кількості:"

            await callback.message.edit_text(
                text,
                reply_markup=get_quantity_change_keyboard(items_info)
            )
            await callback.answer("✅ Кількість збільшено")
        else:
            await callback.answer("❌ Помилка при оновленні кількості")

    except Exception as e:
        logger.error(f"Error in quantity increase: {e}")
        await callback.answer("❌ Помилка при збільшенні кількості")


@user.callback_query(F.data.startswith("qty_decrease_"))
async def quantity_decrease(callback: CallbackQuery):
    """Уменьшает количество товара в меню изменения количества"""
    try:
        article = callback.data.replace("qty_decrease_", "")
        user_cart = await cart.get_cart(callback.from_user.id)

        if not user_cart or article not in user_cart:
            await callback.answer("Товар не знайдено в кошику", show_alert=True)
            return

        current_quantity = user_cart[article]

        if current_quantity <= 1:
            await callback.answer(
                "Щоб видалити товар, використовуйте кнопку видалення",
                show_alert=True
            )
            return

        # Уменьшаем количество
        new_quantity = current_quantity - 1
        success, msg = await cart.update_quantity(
            callback.from_user.id,
            article,
            new_quantity
        )

        if success:
            # Обновляем меню изменения количества
            items_info = []
            text = "📝 Зміна кількості товарів:\n\n"

            updated_cart = await cart.get_cart(callback.from_user.id)
            for cart_article, quantity in updated_cart.items():
                product_info = product_manager.get_product_info(cart_article)
                if product_info:
                    name, price, available = product_info
                    text += (
                        f"📦 {name}\n"
                        f"Артикул: {cart_article}\n"
                        f"Поточна кількість: {quantity} шт.\n"
                        f"Доступно на складі: {available} шт.\n"
                        f"Ціна: {price:.2f} грн. x {quantity} = {price * quantity:.2f} грн.\n"
                        "➖➖➖➖➖➖➖➖➖➖\n\n"
                    )
                    items_info.append({
                        'article': cart_article,
                        'name': name,
                        'quantity': quantity,
                        'available': available
                    })

            text += "Використовуйте кнопки ➕ та ➖ для зміни кількості:"

            await callback.message.edit_text(
                text,
                reply_markup=get_quantity_change_keyboard(items_info)
            )
            await callback.answer("✅ Кількість зменшено")
        else:
            await callback.answer("❌ Помилка при оновленні кількості")

    except Exception as e:
        logger.error(f"Error in quantity decrease: {e}")
        await callback.answer("❌ Помилка при зменшенні кількості")


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
