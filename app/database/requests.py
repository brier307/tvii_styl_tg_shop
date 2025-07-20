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
        items: Dict[str, int], # {barcode: quantity}
        name: str,
        phone: str,
        delivery: DeliveryMethod,
        address: str,
        payment_method: str,
        comment: Optional[str] = None
) -> Optional[Order]:
    """
    Создает новый заказ в базе данных.
    Args:
        items (Dict[str, int]): Словарь товаров {штрих-код: количество}
    """
    logger.info(f"Creating new order for user {tg_id}")
    try:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                logger.error(f"User {tg_id} not found")
                return None

            total_price = 0.0
            product_manager = ProductManager()
            # Расчет суммы по штрих-кодам
            for barcode, quantity in items.items():
                product_info = await product_manager.get_product_info_by_barcode(barcode)
                if product_info:
                    _, price, _, _ = product_info
                    total_price += price * quantity

            utc_plus_3 = timezone('Etc/GMT-3')
            current_time = datetime.now(utc_plus_3)

            new_order = Order(
                tg_id=tg_id,
                articles=json.dumps(items), # Сохраняем {barcode: quantity}
                name=name,
                phone=phone,
                delivery=delivery.value,
                address=address,
                payment_method=payment_method,
                date=current_time,
                status=OrderStatus.NEW.value,
                total_price=total_price,
                comment=comment
            )
            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)
            logger.info(f"Successfully created order #{new_order.id}")
            return new_order
    except Exception as e:
        logger.error(f"Error creating order for user {tg_id}: {e}", exc_info=True)
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


async def update_order_status(order_id: int, status: OrderStatus, tracking_number: Optional[int] = None) -> Optional[
    Order]:
    """
    Обновляет статус заказа и опционально номер отслеживания.

    Args:
        order_id (int): ID заказа.
        status (OrderStatus): Новый статус заказа.
        tracking_number (Optional[int]): Номер для отслеживания (ТТН).

    Returns:
        Optional[Order]: Обновленный заказ или None, если обновление не удалось.
    """
    async with async_session() as session:
        values_to_update = {"status": status.value}
        if tracking_number is not None:
            values_to_update["tracking_number"] = tracking_number

        query = update(Order).where(Order.id == order_id).values(**values_to_update)
        await session.execute(query)
        await session.commit()
        return await get_order(order_id)


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
