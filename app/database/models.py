import enum
from datetime import datetime

from typing import Optional, List
from sqlalchemy import ForeignKey, String, BigInteger, DateTime, JSON, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from config import DB_URL

engine = create_async_engine(url=DB_URL,
                             echo=True)
    
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class OrderStatus(enum.Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED_BY_ADMIN = "cancelled_by_admin"
    CANCELLED_BY_USER = "cancelled_by_user"

    def get_uk_description(self) -> str:
        """Повертає опис статусу українською"""
        descriptions = {
            self.NEW: "В обробці",
            self.CONFIRMED: "Підтверджено",
            self.SHIPPED: "Відправлено",
            self.DELIVERED: "Доставлено",
            self.CANCELLED_BY_ADMIN: "Скасовано адміністратором",
            self.CANCELLED_BY_USER: "Скасовано користувачем",
        }
        return descriptions[self]


class DeliveryMethod(enum.Enum):
    NOVA_POSHTA = "Нова Пошта"
    UKRPOSHTA = "Укрпошта"
    SELF_PICKUP = "Самовивіз"


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Связь с заказами
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'), nullable=False)
    articles: Mapped[str] = mapped_column(JSON, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OrderStatus.NEW.value
    )

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="orders")


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
