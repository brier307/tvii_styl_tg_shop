import pandas as pd
from typing import Optional, Tuple
from pathlib import Path


class ProductManager:
    def __init__(self, file_path: str = "Stock.xls"):
        """
        Инициализация менеджера продуктов

        Args:
            file_path (str): путь к Excel файлу с товарами
        """
        self.file_path = Path(file_path)
        self.df = None
        self._load_data()

    def _load_data(self) -> None:
        """Загрузка данных из Excel файла"""
        try:
            # Загружаем файл, начиная с 7-й строки (skiprows=6)
            self.df = pd.read_excel(
                self.file_path,
                skiprows=6,  # Пропускаем первые 6 строк
                usecols=[
                    "Номенклатура",
                    "Артикул ",  # Оставляем пробел, как в оригинале
                    "Кількість",
                    "У вибраному типі цін (USD)"
                ]
            )
            # Очищаем данные
            self.df = self.df.dropna(subset=["Артикул "])
            # Очищаем пробелы в артикулах
            self.df["Артикул "] = self.df["Артикул "].str.strip()

        except Exception as e:
            print(f"Ошибка при загрузке файла: {e}")
            raise

    def get_product_info(self, article: str) -> Optional[Tuple[str, float, int]]:
        """
        Получить информацию о товаре по артикулу

        Args:
            article (str): артикул товара

        Returns:
            Optional[Tuple[str, float, int]]: кортеж (название, цена, количество) или None, если товар не найден
        """
        try:
            # Поиск товара по артикулу
            product = self.df[self.df["Артикул "] == article]

            if product.empty:
                return None

            name = product["Номенклатура"].iloc[0]
            price = float(product["У вибраному типі цін (USD)"].iloc[0])
            quantity = int(product["Кількість"].iloc[0])

            return (name, price, quantity)

        except Exception as e:
            print(f"Ошибка при получении информации о товаре: {e}")
            return None

    def is_available(self, article: str) -> bool:
        """
        Проверить наличие товара на складе

        Args:
            article (str): артикул товара

        Returns:
            bool: True если товар есть в наличии, False если нет
        """
        product_info = self.get_product_info(article)
        if product_info is None:
            return False
        return product_info[2] > 0

    def get_price(self, article: str) -> Optional[float]:
        """
        Получить цену товара по артикулу

        Args:
            article (str): артикул товара

        Returns:
            Optional[float]: цена товара или None, если товар не найден
        """
        product_info = self.get_product_info(article)
        if product_info is None:
            return None
        return product_info[1]

    def get_name(self, article: str) -> Optional[str]:
        """
        Получить название товара по артикулу

        Args:
            article (str): артикул товара

        Returns:
            Optional[str]: название товара или None, если товар не найден
        """
        product_info = self.get_product_info(article)
        if product_info is None:
            return None
        return product_info[0]

    def refresh_data(self) -> None:
        """Обновить данные из Excel файла"""
        self._load_data()