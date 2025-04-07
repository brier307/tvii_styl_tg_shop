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

    async def add_to_cart(self, tg_id: int, article: str, quantity: int = 1) -> tuple[bool, str]:
        """
        Добавляет товар в корзину

        Args:
            tg_id (int): ID пользователя
            article (str): Артикул товара
            quantity (int): Количество товара

        Returns:
            tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)

            # Получаем текущую корзину
            current_cart = await self.get_cart(tg_id) or {}

            # Обновляем количество
            current_quantity = current_cart.get(article, 0)
            new_quantity = current_quantity + quantity

            # Проверяем ограничение на количество
            if new_quantity > 10:
                return False, "⚠️ Не можна додати більше 10 одиниць одного товару"

            # Обновляем корзину
            current_cart[article] = new_quantity

            # Сохраняем корзину
            await self.redis.set(
                cart_key,
                json.dumps(current_cart),
                ex=int(self.expiration.total_seconds())
            )

            return True, "✅ Товар додано до кошика"

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return False, "⚠️ Помилка підключення до бази даних"
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return False, "⚠️ Помилка при додаванні товару"

    async def get_cart(self, tg_id: int) -> Optional[Dict[str, int]]:
        """
        Получает содержимое корзины

        Args:
            tg_id (int): ID пользователя

        Returns:
            Optional[Dict[str, int]]: Словарь {артикул: количество} или None
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)
            cart_data = await self.redis.get(cart_key)

            if cart_data:
                try:
                    return json.loads(cart_data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in cart data for user {tg_id}")
                    return {}
            return {}

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting cart: {e}")
            return {}

    async def update_quantity(self, tg_id: int, article: str, quantity: int) -> tuple[bool, str]:
        """
        Обновляет количество товара в корзине

        Args:
            tg_id (int): ID пользователя
            article (str): Артикул товара
            quantity (int): Новое количество

        Returns:
            tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            await self.ensure_connection()

            if quantity <= 0:
                return await self.remove_item(tg_id, article)

            if quantity > 10:
                return False, "⚠️ Не можна додати більше 10 одиниць одного товару"

            cart_key = self._get_cart_key(tg_id)
            current_cart = await self.get_cart(tg_id)

            if not current_cart:
                return False, "❌ Кошик порожній"

            if article not in current_cart:
                return False, "❌ Товар не знайдено в кошику"

            # Обновляем количество
            current_cart[article] = quantity

            # Сохраняем корзину
            await self.redis.set(
                cart_key,
                json.dumps(current_cart),
                ex=int(self.expiration.total_seconds())
            )

            return True, "✅ Кількість оновлено"

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return False, "⚠️ Помилка підключення до бази даних"
        except Exception as e:
            logger.error(f"Error updating quantity: {e}")
            return False, "⚠️ Помилка при оновленні кількості"

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
        Очищает корзину

        Args:
            tg_id (int): ID пользователя

        Returns:
            tuple[bool, str]: (успех операции, сообщение)
        """
        try:
            await self.ensure_connection()
            cart_key = self._get_cart_key(tg_id)

            if await self.redis.delete(cart_key):
                return True, "✅ Кошик очищено"
            return False, "❌ Кошик вже порожній"

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return False, "⚠️ Помилка підключення до бази даних"
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False, "⚠️ Помилка при очищенні кошика"
