from typing import Dict, Optional
import json
import redis.asyncio as redis
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class RedisCart:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = None
        self.redis_url = redis_url
        self.cart_prefix = "cart:"
        self.expiration = timedelta(days=1)

    async def init(self):
        """Инициализация подключения к Redis"""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Проверяем подключение
            await self.redis.ping()
            logger.info("Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    async def ensure_connection(self):
        """Проверяет и восстанавливает подключение к Redis при необходимости"""
        if self.redis is None:
            await self.init()
        try:
            if self.redis:
                await self.redis.ping()
            else:
                await self.init()
        except (redis.ConnectionError, AttributeError):
            await self.init()

        if self.redis is None:
            raise redis.ConnectionError("Could not connect to Redis")

    def _get_cart_key(self, tg_id: int) -> str:
        """Генерирует ключ для корзины пользователя"""
        return f"{self.cart_prefix}{tg_id}"

    async def add_item_to_cart(self, tg_id: int, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        """
        Добавляет товар (по штрих-коду) в корзину.
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)
            current_cart = await self.get_cart(tg_id) or {}

            current_quantity = current_cart.get(item_id, 0)
            new_quantity = current_quantity + quantity

            if new_quantity > 999:
                return False, "⚠️ Не можна додати більше 999 одиниць одного товару"

            current_cart[item_id] = new_quantity
            await self.redis.set(
                cart_key,
                json.dumps(current_cart),
                ex=int(self.expiration.total_seconds())
            )
            return True, "✅ Товар додано до кошика"
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return False, "⚠️ Помилка при додаванні товару до кошика"

    async def get_cart(self, tg_id: int) -> Optional[Dict[str, int]]:
        """
        Получает содержимое корзины {item_id: количество}.
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)
            cart_data = await self.redis.get(cart_key)
            return json.loads(cart_data) if cart_data else {}
        except Exception as e:
            logger.error(f"Error getting cart: {e}")
            return {}

    async def update_item_quantity(self, tg_id: int, item_id: str, quantity: int) -> tuple[bool, str]:
        """
        Обновляет количество товара (по штрих-коду) в корзине.
        """
        try:
            await self.ensure_connection()
            if quantity <= 0:
                return await self.remove_item(tg_id, item_id)
            if quantity > 999:
                return False, "⚠️ Не можна додати більше 999 одиниць одного товару"

            cart_key = self._get_cart_key(tg_id)
            current_cart = await self.get_cart(tg_id)
            if not current_cart or item_id not in current_cart:
                return False, "❌ Товар не найден в корзине"

            current_cart[item_id] = quantity
            await self.redis.set(
                cart_key,
                json.dumps(current_cart),
                ex=int(self.expiration.total_seconds())
            )
            return True, "✅ Кількість оновлено"
        except Exception as e:
            logger.error(f"Error updating quantity: {e}")
            return False, "⚠️ Помилка при оновленні кількості товару в кошику"

    async def remove_item(self, tg_id: int, article: str) -> tuple[bool, str]:
        """
        Удаляет товар из корзины

        Args:
            tg_id (int): ID пользователя
            article (str): Артикул товара

        Returns:
            tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)
            current_cart = await self.get_cart(tg_id)

            if not current_cart:
                return False, "❌ Кошик порожній"

            if article not in current_cart:
                return False, "❌ Товар не знайдено в кошику"

            # Удаляем товар
            del current_cart[article]

            # Сохраняем или удаляем корзину
            if current_cart:
                await self.redis.set(
                    cart_key,
                    json.dumps(current_cart),
                    ex=int(self.expiration.total_seconds())
                )
            else:
                await self.redis.delete(cart_key)

            return True, "✅ Товар видалено з кошика"

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return False, "⚠️ Помилка підключення до бази даних"
        except Exception as e:
            logger.error(f"Error removing item: {e}")
            return False, "⚠️ Помилка при видаленні товару"

    async def clear_cart(self, tg_id: int) -> tuple[bool, str]:
        """
        Очищает корзину пользователя.
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)
            if await self.redis.delete(cart_key):
                return True, "✅ Кошик очищено"
            return False, "❌ Корзина уже пуста"
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False, "⚠️ Помилка при очищенні кошика"

