from app.database.models import async_session, User, Order, OrderStatus, DeliveryMethod
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update
from typing import Optional, List, Dict
import json
import logging
from datetime import datetime


from app.database.models import async_session, User, Order, OrderStatus, DeliveryMethod


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
    Создает новый заказ в базе данных.

    Args:
        tg_id (int): Telegram ID пользователя
        articles (Dict[str, int]): Словарь товаров {артикул: количество}
        name (str): ФИО получателя
        phone (str): Номер телефона
        delivery (DeliveryMethod): Способ доставки (enum)
        address (str): Адрес доставки
        payment_method (str): Способ оплаты

    Returns:
        Optional[Order]: Созданный заказ или None в случае ошибки
    """
    logger.info(f"Creating new order for user {tg_id}")
    logger.debug(
        f"Order details: "
        f"articles={articles}, "
        f"name={name}, "
        f"phone={phone}, "
        f"delivery={delivery.value}, "
        f"address={address}, "
        f"payment_method={payment_method}"
    )

    try:
        async with async_session() as session:
            # Проверяем существование пользователя
            query = select(User).where(User.tg_id == tg_id)
            user = await session.scalar(query)

            if not user:
                logger.error(f"User {tg_id} not found in database")
                return None

            logger.debug(f"Found user: {user.id}")

            # Проверяем корректность данных
            if not all([name, phone, address, payment_method, articles]):
                logger.error("Missing required order fields")
                return None

            # Создаем новый заказ
            new_order = Order(
                tg_id=tg_id,
                articles=json.dumps(articles),
                name=name,
                phone=phone,
                delivery=delivery.value,
                address=address,
                payment_method=payment_method,
                date=datetime.utcnow(),
                status=OrderStatus.NEW.value
            )

            # Добавляем заказ в сессию
            session.add(new_order)

            # Коммитим изменения
            await session.commit()

            # Обновляем объект заказа после коммита
            await session.refresh(new_order)

            created_order_id = new_order.id
            logger.info(f"Successfully created order #{created_order_id} for user {tg_id}")

            # Получаем свежую копию заказа
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


async def get_user_orders(tg_id: int) -> List[Order]:
    """Получает все заказы пользователя"""
    async with async_session() as session:
        query = select(Order).where(Order.tg_id == tg_id).order_by(Order.date.desc())
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_order(order_id: int) -> Optional[Order]:
    """Получает заказ по ID"""
    async with async_session() as session:
        query = select(Order).where(Order.id == order_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def update_order_status(order_id: int, status: OrderStatus) -> Optional[Order]:
    """Обновляет статус заказа"""
    async with async_session() as session:
        query = update(Order).where(Order.id == order_id).values(status=status.value)
        await session.execute(query)
        await session.commit()
        return await get_order(order_id)