from app.database.models import async_session, User, Order, OrderStatus, DeliveryMethod
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update
from typing import Optional, List, Dict
import json
import logging
from datetime import datetime
from pytz import timezone

from app.database.models import async_session, User, Order, OrderStatus, DeliveryMethod
from app.database.products import ProductManager

logger = logging.getLogger(__name__)


async def set_user(tg_id: int, name: str = None) -> User:
    """
    Создает нового пользователя или возвращает существующего.

    Args:
        tg_id (int): Telegram ID пользователя
        name (str, optional): Имя пользователя

    Returns:
        User: Объект пользователя
    """
    logger.info(f"Setting up user with tg_id: {tg_id}")

    async with async_session() as session:
        async with session.begin():
            try:
                # Пытаемся найти существующего пользователя
                query = select(User).where(User.tg_id == tg_id)
                user = await session.scalar(query)

                if user:
                    logger.debug(f"Found existing user: {user.id}")
                    # Обновляем имя, если оно предоставлено
                    if name and user.name != name:
                        user.name = name
                        logger.debug(f"Updated name for user {user.id}")
                else:
                    # Создаем нового пользователя
                    logger.debug(f"Creating new user with tg_id: {tg_id}")
                    user = User(tg_id=tg_id, name=name)
                    session.add(user)

                await session.commit()
                return user

            except Exception as e:
                logger.error(f"Error setting up user {tg_id}: {str(e)}", exc_info=True)
                await session.rollback()
                raise


async def get_user(tg_id: int) -> Optional[User]:
    """Получает пользователя по Telegram ID"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user


async def update_user(tg_id: int, **kwargs) -> Optional[User]:
    """Обновляет данные пользователя"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            await session.commit()
            return user
    return None


async def update_user_name(tg_id: int, name: str) -> Optional[User]:
    """Обновляет имя пользователя"""
    return await update_user(tg_id, name=name)


async def update_user_phone(tg_id: int, phone: str) -> Optional[User]:
    """Обновляет номер телефона пользователя"""
    return await update_user(tg_id, phone=phone)


async def create_order(
        tg_id: int,
        articles: Dict[str, int],
        name: str,
        phone: str,
        delivery: DeliveryMethod,
        address: str,
        payment_method: str
) -> Optional[Order]:
    """
    Створює нове замовлення у базі даних.

    Args:
        tg_id (int): Telegram ID користувача
        articles (Dict[str, int]): Словник товарів {артикул: кількість}
        name (str): ПІБ отримувача
        phone (str): Номер телефону
        delivery (DeliveryMethod): Спосіб доставки (enum)
        address (str): Адреса доставки
        payment_method (str): Спосіб оплати

    Returns:
        Optional[Order]: Створене замовлення або None у разі помилки
    """
    logger.info(f"Creating new order for user {tg_id}")

    try:
        async with async_session() as session:
            # Перевіряємо існування користувача
            query = select(User).where(User.tg_id == tg_id)
            user = await session.scalar(query)

            if not user:
                logger.error(f"User {tg_id} not found in database")
                return None

            logger.debug(f"Found user: {user.id}")

            # Обчислюємо загальну суму замовлення
            total_price = 0.0
            product_manager = ProductManager()  # Ініціалізуємо ProductManager
            for article, quantity in articles.items():
                product_info = product_manager.get_product_info(article)
                if product_info:
                    _, price, _ = product_info
                    total_price += price * quantity

            # Встановлюємо дату у часовому поясі UTC+3
            utc_plus_3 = timezone('Etc/GMT-3')
            current_time = datetime.now(utc_plus_3)

            # Створюємо нове замовлення
            new_order = Order(
                tg_id=tg_id,
                articles=json.dumps(articles),
                name=name,
                phone=phone,
                delivery=delivery.value,
                address=address,
                payment_method=payment_method,
                date=current_time,  # Використовуємо дату з часовим поясом UTC+3
                status=OrderStatus.NEW.value,
                total_price=total_price  # Зберігаємо суму замовлення
            )

            # Додаємо замовлення до сесії
            session.add(new_order)

            # Коммітимо зміни
            await session.commit()

            # Оновлюємо об'єкт замовлення після комміта
            await session.refresh(new_order)

            created_order_id = new_order.id
            logger.info(f"Successfully created order #{created_order_id} for user {tg_id}")

            # Отримуємо свіжу копію замовлення
            query = select(Order).where(Order.id == created_order_id)
            final_order = await session.scalar(query)

            return final_order

    except SQLAlchemyError as e:
        logger.error(
            f"Database error while creating order for user {tg_id}: {str(e)}",
            exc_info=True
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error while creating order for user {tg_id}: {str(e)}",
            exc_info=True
        )
        return None


async def get_order(order_id: int) -> Optional[Order]:
    """
    Отримує замовлення за його ID.

    Args:
        order_id (int): ID замовлення

    Returns:
        Optional[Order]: Замовлення або None, якщо не знайдено
    """
    async with async_session() as session:
        query = select(Order).where(Order.id == order_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def update_order_status(order_id: int, status: OrderStatus) -> Optional[Order]:
    """
    Обновляет статус заказа.

    Args:
        order_id (int): ID заказа.
        status (OrderStatus): Новый статус заказа.

    Returns:
        Optional[Order]: Обновленный заказ или None, если обновление не удалось.
    """
    async with async_session() as session:
        query = update(Order).where(Order.id == order_id).values(status=status.value)
        await session.execute(query)
        await session.commit()
        return await get_order(order_id)  # Возвращаем обновленный заказ


async def get_user_orders(tg_id: int) -> List[Order]:
    """
    Получает все заказы пользователя, отсортированные по дате.

    Args:
        tg_id (int): Telegram ID пользователя

    Returns:
        List[Order]: Список заказов
    """
    async with async_session() as session:
        query = select(Order).where(Order.tg_id == tg_id).order_by(Order.date.desc())
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_all_orders():
    """Отримує всі замовлення з бази даних."""
    async with async_session() as session:
        query = select(Order).order_by(Order.date.desc())  # Конструктор запиту
        result = await session.execute(query)
        return result.scalars().all()  # Повертає всі записи як об'єкти ORM


async def get_orders_by_status(status: str):
    """
    Отримує замовлення за заданим статусом.
    """
    async with async_session() as session:
        query = select(Order).where(Order.status == status).order_by(Order.date.desc())
        result = await session.execute(query)
        return result.scalars().all()
