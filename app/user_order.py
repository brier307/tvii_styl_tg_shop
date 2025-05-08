import logging
import datetime
import re

from math import ceil
from aiogram import Router, F
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

from app.database.models import DeliveryMethod
from app.database.requests import create_order, get_user_orders
from app.database.redis_cart import RedisCart
from app.database.products import ProductManager
from aiogram.filters.state import State, StatesGroup
from app.user_keyboards import get_orders_keyboard, get_back_to_main_menu


ORDERS_PER_PAGE = 5  # Количество заказов на одной странице


# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Создаем форматтер для логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаем обработчик для записи в файл
file_handler = logging.FileHandler('order_processing.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class OrderStates(StatesGroup):
    DELIVERY_METHOD = State()
    NOVA_POSHTA_CITY = State()
    NOVA_POSHTA_OFFICE = State()
    UKRPOSHTA_INDEX = State()
    RECIPIENT_NAME = State()
    PHONE_NUMBER = State()
    PAYMENT_METHOD = State()
    CONFIRMATION = State()


class OrderManager:
    def __init__(self, router: Router):
        self.router = router
        self.cart = RedisCart()
        self.product_manager = ProductManager()
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация обработчиков для заказа"""
        # Меняем "create_order" на "checkout" для соответствия существующей клавиатуре
        self.router.callback_query.register(
            self.start_order,
            F.data == "checkout"  # Используем существующий callback_data
        )
        self.router.callback_query.register(
            self.process_delivery_method,
            F.data.startswith("delivery_")
        )
        self.router.message.register(
            self.process_nova_poshta_city,
            OrderStates.NOVA_POSHTA_CITY
        )
        self.router.message.register(
            self.process_nova_poshta_office,
            OrderStates.NOVA_POSHTA_OFFICE
        )
        self.router.message.register(
            self.process_ukrposhta_index,
            OrderStates.UKRPOSHTA_INDEX
        )
        self.router.message.register(
            self.process_recipient_name,
            OrderStates.RECIPIENT_NAME
        )
        self.router.message.register(
            self.process_phone_number,
            OrderStates.PHONE_NUMBER
        )
        self.router.callback_query.register(
            self.process_payment_method,
            F.data.startswith("payment_")
        )
        self.router.callback_query.register(
            self.process_confirmation,
            F.data.in_({"confirm_order", "cancel_order"})
        )
        self.router.callback_query.register(
            self.process_back,
            F.data == "order_back"
        )
        self.router.callback_query.register(
            self.cancel_order,
            F.data == "order_cancel"
        )

    @staticmethod
    def create_delivery_keyboard() -> InlineKeyboardMarkup:
        """Создает клавиатуру выбора способа доставки"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚚 Нова Пошта",
                                  callback_data="delivery_nova_poshta")],
            [InlineKeyboardButton(text="📬 Укрпошта",
                                  callback_data="delivery_ukrposhta")],
            [InlineKeyboardButton(text="🏪 Самовивіз",
                                  callback_data="delivery_self_pickup")],
            [InlineKeyboardButton(text="❌ Скасувати",
                                  callback_data="order_cancel")]
        ])
        return keyboard

    @staticmethod
    def create_payment_keyboard() -> InlineKeyboardMarkup:
        """Создает клавиатуру выбора способа оплаты"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Онлайн оплата",
                                  callback_data="payment_online")],
            [InlineKeyboardButton(text="💵 Післяоплата",
                                  callback_data="payment_cash")],
            [InlineKeyboardButton(text="⬅️ Назад",
                                  callback_data="order_back")],
            [InlineKeyboardButton(text="❌ Скасувати",
                                  callback_data="order_cancel")]
        ])
        return keyboard

    @staticmethod
    def create_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Создает клавиатуру подтверждения заказа"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Підтвердити",
                                     callback_data="confirm_order"),
                InlineKeyboardButton(text="❌ Скасувати",
                                     callback_data="cancel_order")
            ],
            [InlineKeyboardButton(text="⬅️ Назад",
                                  callback_data="order_back")]
        ])
        return keyboard

    @staticmethod
    def create_back_keyboard() -> InlineKeyboardMarkup:
        """Создает клавиатуру с кнопкой назад"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад",
                                  callback_data="order_back")],
            [InlineKeyboardButton(text="❌ Скасувати",
                                  callback_data="order_cancel")]
        ])
        return keyboard

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Проверяет корректность номера телефона"""
        pattern = r'^\+?3?8?(0\d{9})$'
        return bool(re.match(pattern, phone))

    @staticmethod
    def validate_post_index(index: str) -> bool:
        """Проверяет корректность почтового индекса"""
        return bool(re.match(r'^\d{5}$', index))

    async def format_order_details(self, user_id: int, state: FSMContext) -> str:
        """Форматирует детали заказа"""
        data = await state.get_data()
        cart_items = await self.cart.get_cart(user_id)

        total = 0
        items_text = []

        for article, quantity in cart_items.items():
            product_info = self.product_manager.get_product_info(article)
            if product_info:
                name, price, _ = product_info
                subtotal = price * quantity
                total += subtotal
                items_text.append(f"- {name} x{quantity} = {subtotal:.2f} грн")

        # Получаем значение enum для отображения
        delivery_method_name = DeliveryMethod[data['delivery_method']].value

        details = [
            "📦 Деталі замовлення:",
            "\nТовари:",
            *items_text,
            f"\n💰 Загальна сума: {total:.2f} грн",
            f"\n🚚 Спосіб доставки: {delivery_method_name}",
            f"📍 Адреса: {data.get('address', '')}",
            f"👤 Отримувач: {data.get('name', '')}",
            f"📱 Телефон: {data.get('phone', '')}",
            f"💳 Спосіб оплати: {data.get('payment_method', '')}"
        ]

        return "\n".join(details)

    async def start_order(self, callback: CallbackQuery, state: FSMContext):
        """Начинает процесс оформления заказа"""
        logger.info(f"Starting order process for user {callback.from_user.id}")

        # Проверяем наличие товаров в корзине
        cart_items = await self.cart.get_cart(callback.from_user.id)
        if not cart_items:
            logger.warning(f"User {callback.from_user.id} tried to create order with empty cart")
            await callback.answer("Ваша корзина пуста!")
            return

        logger.debug(f"Cart items for user {callback.from_user.id}: {cart_items}")
        await state.set_state(OrderStates.DELIVERY_METHOD)
        await callback.message.edit_text(
            "Оберіть спосіб доставки:",
            reply_markup=self.create_delivery_keyboard()
        )

    async def process_delivery_method(self, callback: CallbackQuery, state: FSMContext):
        """
        Обрабатывает выбор способа доставки.

        Args:
            callback (CallbackQuery): Callback запрос от нажатия кнопки
            state (FSMContext): Контекст состояния FSM
        """
        user_id = callback.from_user.id
        delivery_method = callback.data.replace('delivery_', '')

        logger.info(f"User {user_id} selected delivery method: {delivery_method}")

        try:
            # Маппинг callback_data в значения enum
            delivery_mapping = {
                'nova_poshta': {
                    'enum': DeliveryMethod.NOVA_POSHTA,
                    'next_state': OrderStates.NOVA_POSHTA_CITY,
                    'message': "Введіть назву населеного пункту:"
                },
                'ukrposhta': {
                    'enum': DeliveryMethod.UKRPOSHTA,
                    'next_state': OrderStates.UKRPOSHTA_INDEX,
                    'message': "Введіть п'ятизначний індекс відділення:"
                },
                'self_pickup': {
                    'enum': DeliveryMethod.SELF_PICKUP,
                    'next_state': OrderStates.RECIPIENT_NAME,
                    'message': "Введіть ПІБ отримувача:"
                }
            }

            # Проверяем валидность выбранного метода доставки
            if delivery_method not in delivery_mapping:
                logger.error(f"Invalid delivery method selected by user {user_id}: {delivery_method}")
                await callback.answer(
                    "Помилка: Невірний спосіб доставки. Спробуйте ще раз.",
                    show_alert=True
                )
                return

            selected_delivery = delivery_mapping[delivery_method]

            # Сохраняем данные о способе доставки
            await state.update_data({
                'delivery_method': selected_delivery['enum'].name,
                'delivery_display_name': selected_delivery['enum'].value
            })

            logger.debug(
                f"Saved delivery method for user {user_id}: "
                f"enum={selected_delivery['enum'].name}, "
                f"display_name={selected_delivery['enum'].value}"
            )

            # Для самовывоза сразу устанавливаем адрес
            if delivery_method == 'self_pickup':
                await state.update_data(address="Самовивіз")
                logger.debug(f"Set self pickup address for user {user_id}")

            # Устанавливаем следующее состояние и отправляем сообщение
            await state.set_state(selected_delivery['next_state'])

            # Создаем клавиатуру с кнопками навигации
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="order_back"
                )],
                [InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="order_cancel"
                )]
            ])

            # Отправляем сообщение с инструкцией для следующего шага
            await callback.message.edit_text(
                text=selected_delivery['message'],
                reply_markup=keyboard
            )

            logger.info(
                f"Successfully processed delivery method for user {user_id}. "
                f"Next state: {selected_delivery['next_state']}"
            )

        except Exception as e:
            logger.error(
                f"Error processing delivery method for user {user_id}: {str(e)}",
                exc_info=True
            )

            # Отправляем сообщение об ошибке пользователю
            error_message = (
                "❌ Виникла помилка при виборі способу доставки.\n"
                "Будь ласка, спробуйте ще раз або зверніться до підтримки."
            )

            try:
                await callback.message.edit_text(
                    text=error_message,
                    reply_markup=self.create_delivery_keyboard()
                )
            except Exception as edit_error:
                logger.error(
                    f"Error sending error message to user {user_id}: {str(edit_error)}",
                    exc_info=True
                )
                await callback.answer(
                    "Виникла помилка. Спробуйте ще раз.",
                    show_alert=True
                )


    async def process_nova_poshta_city(self, message: Message, state: FSMContext):
        """Обрабатывает ввод города для Новой Почты"""
        await state.update_data(nova_poshta_city=message.text.strip())
        await state.set_state(OrderStates.NOVA_POSHTA_OFFICE)
        await message.answer(
            "Введіть номер відділення:",
            reply_markup=self.create_back_keyboard()
        )

    async def process_nova_poshta_office(self, message: Message, state: FSMContext):
        """Обрабатывает ввод отделения Новой Почты"""
        office = message.text.strip()
        data = await state.get_data()
        city = data.get('nova_poshta_city', '')

        address = f"{city}, Відділення {office}"
        await state.update_data(address=address)

        await state.set_state(OrderStates.RECIPIENT_NAME)
        await message.answer(
            "Введіть ПІБ отримувача:",
            reply_markup=self.create_back_keyboard()
        )

    async def process_ukrposhta_index(self, message: Message, state: FSMContext):
        """Обрабатывает ввод индекса Укрпочты"""
        index = message.text.strip()

        if not self.validate_post_index(index):
            await message.answer(
                "Некоректний індекс. Будь ласка, введіть п'ятизначний індекс:",
                reply_markup=self.create_back_keyboard()
            )
            return

        await state.update_data(address=f"Індекс: {index}")
        await state.set_state(OrderStates.RECIPIENT_NAME)
        await message.answer(
            "Введіть ПІБ отримувача:",
            reply_markup=self.create_back_keyboard()
        )

    async def process_recipient_name(self, message: Message, state: FSMContext):
        """Обрабатывает ввод ФИО получателя"""
        name = message.text.strip()

        if len(name.split()) < 2:
            await message.answer(
                "Будь ласка, введіть повне ПІБ (прізвище та ім'я обов'язково):",
                reply_markup=self.create_back_keyboard()
            )
            return

        await state.update_data(name=name)
        await state.set_state(OrderStates.PHONE_NUMBER)

        # Создаем клавиатуру с кнопкой запроса контакта
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поділитися контактом", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        # Создаем inline клавиатуру для навигации
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="order_back")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="order_cancel")]
        ])

        # Отправляем два сообщения:
        # 1. С клавиатурой для контакта
        await message.answer(
            "📱 Натисніть кнопку 'Поділитися контактом' або введіть номер телефону вручну:",
            reply_markup=contact_keyboard
        )

        # 2. С кнопками навигации
        await message.answer(
            "⬅️ Для повернення або скасування використовуйте кнопки нижче:",
            reply_markup=inline_keyboard
        )

    async def process_phone_number(self, message: Message, state: FSMContext):
        """Обрабатывает ввод номера телефона"""
        try:
            if message.contact:
                phone = message.contact.phone_number
            else:
                phone = message.text.strip()

            if not self.validate_phone(phone):
                await message.answer(
                    "Некоректний номер телефону. Будь ласка, введіть номер у форматі +380XXXXXXXXX",
                    reply_markup=self.create_back_keyboard()
                )
                return

            await state.update_data(phone=phone)
            await state.set_state(OrderStates.PAYMENT_METHOD)

            # Убираем клавиатуру с кнопкой контакта
            await message.answer(
                "Оберіть спосіб оплати:",
                reply_markup=ReplyKeyboardRemove()  # Убираем reply клавиатуру
            )

            # Показываем клавиатуру выбора способа оплаты
            await message.answer(
                "Доступні способи оплати:",
                reply_markup=self.create_payment_keyboard()
            )

        except Exception as e:
            print(f"Error in process_phone_number: {e}")
            await message.answer(
                "Виникла помилка при обробці номера телефону. Спробуйте ще раз.",
                reply_markup=self.create_back_keyboard()
            )

    async def cancel_order(self, callback: CallbackQuery, state: FSMContext):
        """Отменяет создание заказа"""
        await state.clear()
        await callback.message.edit_text(
            "❌ Оформлення замовлення скасовано."
        )
        # Убираем клавиатуру с кнопкой контакта
        await callback.message.answer(
            "Повернення до головного меню...",
            reply_markup=ReplyKeyboardRemove()
        )

    async def process_back(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает возврат на предыдущий шаг"""
        current_state = await state.get_state()

        # Если возвращаемся с шага ввода телефона, убираем клавиатуру с контактом
        if current_state == OrderStates.PHONE_NUMBER.state:
            await callback.message.answer(
                "Повернення до попереднього кроку...",
                reply_markup=ReplyKeyboardRemove()
            )

        states_map = {
            OrderStates.NOVA_POSHTA_OFFICE: (OrderStates.NOVA_POSHTA_CITY,
                                             "Введіть назву населеного пункту:"),
            OrderStates.RECIPIENT_NAME: (OrderStates.DELIVERY_METHOD,
                                         "Оберіть спосіб доставки:"),
            OrderStates.PHONE_NUMBER: (OrderStates.RECIPIENT_NAME,
                                       "Введіть ПІБ отримувача:"),
            OrderStates.PAYMENT_METHOD: (OrderStates.PHONE_NUMBER,
                                         "Введіть номер телефону:"),
            OrderStates.CONFIRMATION: (OrderStates.PAYMENT_METHOD,
                                       "Оберіть спосіб оплати:")
        }

        if current_state in states_map:
            new_state, message_text = states_map[current_state]
            await state.set_state(new_state)
            await callback.message.edit_text(
                message_text,
                reply_markup=self.create_back_keyboard()
            )

    async def process_payment_method(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает выбор способа оплаты"""
        payment_method = callback.data.replace('payment_', '')

        if payment_method == 'online':
            await callback.answer(
                "На жаль, онлайн оплата тимчасово недоступна. "
                "Оберіть інший спосіб оплати.",
                show_alert=True
            )
            return

        await state.update_data(payment_method='Післяоплата')

        # Показываем итоговую информацию о заказе
        order_details = await self.format_order_details(
            callback.from_user.id,
            state
        )

        await callback.message.edit_text(
            f"{order_details}\n\nПідтвердіть оформлення замовлення:",
            reply_markup=self.create_confirmation_keyboard()
        )
        await state.set_state(OrderStates.CONFIRMATION)

    async def process_confirmation(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает подтверждение заказа"""
        user_id = callback.from_user.id
        logger.info(f"Processing order confirmation for user {user_id}")

        if callback.data == "confirm_order":
            try:
                data = await state.get_data()
                logger.debug(f"Order data for user {user_id}: {data}")

                cart_items = await self.cart.get_cart(user_id)
                logger.debug(f"Cart items for user {user_id}: {cart_items}")

                if not cart_items:
                    logger.error(f"Empty cart for user {user_id} during confirmation")
                    await callback.message.edit_text(
                        "❌ Помилка: кошик порожній. Будь ласка, додайте товари перед оформленням замовлення."
                    )
                    return

                # Получаем enum по имени из сохраненных данных
                delivery_method = DeliveryMethod[data['delivery_method']]
                logger.debug(f"Delivery method enum for user {user_id}: {delivery_method}")

                # Создаем заказ в базе данных
                logger.info(f"Creating order in database for user {user_id}")
                order = await create_order(
                    tg_id=user_id,
                    articles=cart_items,
                    name=data['name'],
                    phone=data['phone'],
                    delivery=delivery_method,
                    address=data['address'],
                    payment_method=data['payment_method']
                )

                if order:
                    logger.info(f"Successfully created order #{order.id} for user {user_id}")
                    # Очищаем корзину
                    await self.cart.clear_cart(user_id)
                    await callback.message.edit_text(
                        f"✅ Замовлення #{order.id} успішно оформлено!\n\n"
                        "Ми зв'яжемося з вами найближчим часом для підтвердження замовлення."
                    )
                else:
                    logger.error(f"Failed to create order for user {user_id}")
                    await callback.message.edit_text(
                        "❌ Помилка при оформленні замовлення.\n"
                        "Будь ласка, спробуйте пізніше або зверніться до підтримки."
                    )

            except Exception as e:
                logger.error(
                    f"Error during order confirmation for user {user_id}: {str(e)}",
                    exc_info=True
                )
                await callback.message.edit_text(
                    "❌ Помилка при оформленні замовлення.\n"
                    "Будь ласка, спробуйте пізніше або зверніться до підтримки."
                )

        await state.clear()
        logger.info(f"Cleared state for user {user_id}")


    async def process_back(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает возврат на предыдущий шаг"""
        current_state = await state.get_state()

        states_map = {
            OrderStates.NOVA_POSHTA_OFFICE: (OrderStates.NOVA_POSHTA_CITY,
                                             "Введіть назву населеного пункту:"),
            OrderStates.RECIPIENT_NAME: (OrderStates.DELIVERY_METHOD,
                                         "Оберіть спосіб доставки:"),
            OrderStates.PHONE_NUMBER: (OrderStates.RECIPIENT_NAME,
                                       "Введіть ПІБ отримувача:"),
            OrderStates.PAYMENT_METHOD: (OrderStates.PHONE_NUMBER,
                                         "Введіть номер телефону:"),
            OrderStates.CONFIRMATION: (OrderStates.PAYMENT_METHOD,
                                       "Оберіть спосіб оплати:")
        }


        if current_state in states_map:
            new_state, message_text = states_map[current_state]
            await state.set_state(new_state)
            await callback.message.edit_text(
                message_text,
                reply_markup=self.create_back_keyboard()
            )

    async def cancel_order(self, callback: CallbackQuery, state: FSMContext):
        """Отменяет создание заказа"""
        await state.clear()
        await callback.message.edit_text("❌ Оформлення замовлення скасовано.")


async def process_show_orders(callback: CallbackQuery):
    """Обрабатывает запрос на отображение заказов пользователя."""
    user_id = callback.from_user.id
    orders = await get_user_orders(user_id)

    if not orders:
        await callback.message.edit_text(
            "❌ Ви ще не маєте жодного замовлення.",
            reply_markup=get_back_to_main_menu()
        )
        return

    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = 1

    # Получаем заказы для текущей страницы
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Ваші замовлення:",
        reply_markup=keyboard
    )


async def process_orders_pagination(callback: CallbackQuery):
    """Обрабатывает навигацию по страницам заказов."""
    user_id = callback.from_user.id
    orders = await get_user_orders(user_id)

    total_pages = ceil(len(orders) / ORDERS_PER_PAGE)
    page = int(callback.data.split(":")[1])

    # Получаем заказы для текущей страницы
    start = (page - 1) * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_on_page = orders[start:end]

    keyboard = get_orders_keyboard(orders_on_page, page, total_pages)

    await callback.message.edit_text(
        "📦 Ваші замовлення:",
        reply_markup=keyboard
    )