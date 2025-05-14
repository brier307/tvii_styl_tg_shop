import pandas as pd
from typing import Optional, Tuple, Dict, List
from pathlib import Path


class ProductManager:
    def __init__(self, file_path: str = "Залишки номенклатури.xlsx"):
        """
        Ініціалізація менеджера продуктів

        Args:
            file_path (str): шлях до Excel файлу з товарами
        """
        self.file_path = Path(file_path)
        self.df = None
        self._load_data()

    def _load_data(self) -> None:
        """Завантаження даних з Excel файлу"""
        try:
            # Завантажуємо файл, починаючи з другої строки (header=1)
            self.df = pd.read_excel(
                self.file_path,
                header=1,  # Заголовки знаходяться у другій строкі
                usecols=[
                    "Номенклатура",
                    "Артикул",
                    "Кількість\n(залишок)",
                    "Ціна"
                ]
            )

            # Очищаємо дані
            self.df = self.df.dropna(subset=["Номенклатура"])
            # Видаляємо пробіли в артикулах, якщо вони є
            self.df["Артикул"] = self.df["Артикул"].astype(str).str.strip()
            # Замінюємо 'nan' на пусту строку для артикулів
            self.df.loc[self.df["Артикул"] == 'nan', "Артикул"] = ''

            # Преобразуємо числові колонки
            self.df["Кількість\n(залишок)"] = pd.to_numeric(self.df["Кількість\n(залишок)"], errors='coerce').fillna(0)
            self.df["Ціна"] = pd.to_numeric(self.df["Ціна"], errors='coerce').fillna(0)

        except Exception as e:
            print(f"Помилка при завантаженні файлу: {e}")
            raise

    def get_product_details(self, article: str) -> Optional[dict]:
        """
        Отримати детальну інформацію про товар, включаючи специфікації.

        Args:
            article (str): Артикул товару.

        Returns:
            Optional[dict]: Словник із деталями товару та специфікаціями,
                            або None, якщо товар не знайдено.
        """
        try:
            if not article or article.strip() == '':
                return None

            # Знаходимо всі товари з вказаним артикулом
            products = self.df[self.df["Артикул"] == article.strip()]

            if products.empty:
                return None

            # Основна інформація про товар
            name = products["Номенклатура"].iloc[0].split("(")[0].strip()  # Базова назва без специфікацій
            price = float(products["Ціна"].iloc[0])

            # Формуємо список специфікацій
            specifications = []
            for _, row in products.iterrows():
                # Парсимо специфікацію від першої "(" і до кінця, навіть якщо немає ")"
                spec_index = row["Номенклатура"].find("(")
                if spec_index != -1:
                    spec_name = row["Номенклатура"][spec_index:].strip()
                else:
                    spec_name = ""  # Якщо дужки немає взагалі

                specification = {
                    "specification": spec_name.rstrip(")"),  # Видаляємо зайву дужку, якщо вона є
                    "quantity": int(row["Кількість\n(залишок)"]),
                    "price": float(row["Ціна"]),
                }
                specifications.append(specification)

            return {
                "name": name,
                "article": article,
                "price": price,
                "specifications": specifications,
            }

        except Exception as e:
            print(f"Помилка при отриманні деталей товару: {e}")
            return None

    def get_product_info(self, article: str) -> Optional[Tuple[str, float, int]]:
        """
        Отримати інформацію про товар за артикулом.

        Args:
            article (str): Артикул товару.

        Returns:
            Optional[Tuple[str, float, int]]: Кортеж (назва, ціна, кількість) або None, якщо товар не знайдено.
        """
        try:
            if not article or article.strip() == '':
                return None

            # Пошук товару за артикулом
            product = self.df[self.df["Артикул"] == article.strip()]

            if product.empty:
                return None

            name = product["Номенклатура"].iloc[0]
            price = float(product["Ціна"].iloc[0])
            quantity = int(product["Кількість\n(залишок)"].iloc[0])

            return (name, price, quantity)

        except Exception as e:
            print(f"Помилка при отриманні інформації про товар: {e}")
            return None

    def is_available(self, article: str) -> bool:
        """
        Перевірити наявність товару на складі.

        Args:
            article (str): Артикул товару.

        Returns:
            bool: True, якщо товар є в наявності, False, якщо ні.
        """
        product_info = self.get_product_info(article)
        if product_info is None:
            return False
        return product_info[2] > 0

    def get_price(self, article: str) -> Optional[float]:
        """
        Отримати ціну товару за артикулом.

        Args:
            article (str): Артикул товару.

        Returns:
            Optional[float]: Ціна товару або None, якщо товар не знайдено.
        """
        product_info = self.get_product_info(article)
        if product_info is None:
            return None
        return product_info[1]

    def get_name(self, article: str) -> Optional[str]:
        """
        Отримати назву товару за артикулом.

        Args:
            article (str): Артикул товару.

        Returns:
            Optional[str]: Назва товару або None, якщо товар не знайдено.
        """
        product_info = self.get_product_info(article)
        if product_info is None:
            return None
        return product_info[0]

    def refresh_data(self) -> None:
        """Оновити дані з Excel файлу."""
        self._load_data()