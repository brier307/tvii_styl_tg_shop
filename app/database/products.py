import pandas as pd
from typing import Optional, Tuple
from pathlib import Path


class ProductManager:
    def __init__(self, file_path: str = "Залишки номенклатури.xlsx"):
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
            # Загружаем файл, начиная со второй строки (header=1)
            self.df = pd.read_excel(
                self.file_path,
                header=1,  # Заголовки находятся во второй строке
                usecols=[
                    "Номенклатура",
                    "Артикул",
                    "Кількість\n(залишок)",
                    "Ціна"
                ]
            )

            # Очищаем данные
            self.df = self.df.dropna(subset=["Номенклатура"])
            # Очищаем пробелы в артикулах, если они есть
            self.df["Артикул"] = self.df["Артикул"].astype(str).str.strip()
            # Заменяем 'nan' на пустую строку для артикулов
            self.df.loc[self.df["Артикул"] == 'nan', "Артикул"] = ''

            # Преобразуем числовые колонки
            self.df["Кількість\n(залишок)"] = pd.to_numeric(self.df["Кількість\n(залишок)"], errors='coerce').fillna(0)
            self.df["Ціна"] = pd.to_numeric(self.df["Ціна"], errors='coerce').fillna(0)

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
            if not article or article.strip() == '':
                return None

            # Поиск товара по артикулу
            product = self.df[self.df["Артикул"] == article.strip()]

            if product.empty:
                return None

            name = product["Номенклатура"].iloc[0]
            price = float(product["Ціна"].iloc[0])
            quantity = int(product["Кількість\n(залишок)"].iloc[0])

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