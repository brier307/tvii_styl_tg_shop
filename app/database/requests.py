from app.database.models import async_session, User
from sqlalchemy import select, update
from typing import Optional


async def set_user(tg_id: int) -> User:
    """Создает нового пользователя или возвращает существующего"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if not user:
            user = User(tg_id=tg_id)
            session.add(user)
            await session.commit()

        return user


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