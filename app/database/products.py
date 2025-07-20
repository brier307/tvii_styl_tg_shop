import pandas as pd
from typing import Optional, Tuple, Dict, List
from pathlib import Path
import asyncio
# Імпорти zipfile та shutil видалено, оскільки перепакування більше не потрібне
from config import PATH_TO_STOCK
import xlrd  # Переконайтесь, що бібліотека xlrd встановлена для читання .xls файлів


class ProductManager:
    def __init__(self, file_path: str = PATH_TO_STOCK):
        """
        Ініціалізація менеджера продуктів.
        Args:
            file_path (str): шлях до Excel файлу з товарами (.xls).
        """
        self.file_path = Path(file_path)
        self.df = None

    def _load_data_sync(self):
        if not self.file_path.is_file():
            raise FileNotFoundError(f"Файл не найден: {self.file_path}")

        self.df = pd.read_excel(
            self.file_path,
            header=1,
            engine='xlrd',
            usecols=[
                "Номенклатура",
                "Артикул",
                "Кількість\n(залишок)",
                "Ціна",
                "Штрихкод"
            ]
        )
        self.df = self.df.dropna(subset=["Номенклатура"])
        self.df["Артикул"] = self.df["Артикул"].astype(str).str.strip()
        self.df["Штрихкод"] = self.df["Штрихкод"].astype(str).str.strip()
        self.df.loc[self.df["Артикул"] == 'nan', "Артикул"] = ''
        self.df.loc[self.df["Штрихкод"] == 'nan', "Штрихкод"] = ''
        self.df["Кількість\n(залишок)"] = pd.to_numeric(self.df["Кількість\n(залишок)"], errors='coerce').fillna(0)
        self.df["Ціна"] = pd.to_numeric(self.df["Ціна"], errors='coerce').fillna(0)


    async def _load_data(self) -> bool:
        """
        Асинхронно завантажує дані з Excel файлу, виконуючи синхронний
        блокуючий код в окремому потоці.
        """
        try:
            # Виконуємо важку операцію вводу-виводу в потоці
            await asyncio.to_thread(self._load_data_sync)
            return True
        except Exception as e:
            print(f"ПОМИЛКА при завантаженні та обробці файлу: {e}")
            self.df = None
            return False

    async def get_product_details_by_barcode(self, barcode: str) -> Optional[dict]:
        """
        Отримати детальну інформацію про товар за штрих-кодом.
        """
        if not await self._load_data() or self.df is None:
            return None
        try:
            if not barcode or not str(barcode).strip():
                return None

            products = self.df[self.df["Штрихкод"] == str(barcode).strip()]
            if products.empty:
                return None

            first_product = products.iloc[0]
            name = first_product["Номенклатура"].split("(")[0].strip()
            price = float(first_product["Ціна"])
            article = str(first_product["Артикул"])

            specifications = []
            for _, row in products.iterrows():
                spec_index = row["Номенклатура"].find("(")
                spec_name = row["Номенклатура"][spec_index:].strip() if spec_index != -1 else ""
                specifications.append({
                    "specification": spec_name.rstrip(")"),
                    "quantity": int(row["Кількість\n(залишок)"]),
                    "price": float(row["Ціна"]),
                    "barcode": str(row["Штрихкод"])
                })
            return {
                "name": name,
                "article": article,
                "price": price,
                "specifications": specifications,
            }
        except Exception as e:
            print(f"Помилка при отриманні деталей товару за штрих-кодом: {e}")
            return None

    async def get_product_info_by_barcode(self, barcode: str) -> Optional[Tuple[str, float, int, str]]:
        """
        Отримати базову інформацію про товар за штрих-кодом.
        Повертає: (Назва, Ціна, Кількість, Артикул)
        """
        if not await self._load_data() or self.df is None:
            return None
        try:
            product_row = self.df[self.df["Штрихкод"] == str(barcode).strip()]
            if product_row.empty:
                return None

            first_row = product_row.iloc[0]
            name = first_row["Номенклатура"]
            price = float(first_row["Ціна"])
            quantity = int(first_row["Кількість\n(залишок)"])
            article = str(first_row["Артикул"])

            return (name, price, quantity, article)
        except Exception as e:
            print(f"Ошибка при получении информации о товаре по штрих-коду: {e}")
            return None


    async def get_product_details(self, article: str) -> Optional[dict]:
        """
        Отримати детальну інформацію про товар, включаючи специфікації та штрихкод.
        """
        if not await self._load_data() or self.df is None:
            return None

        try:
            if not article or article.strip() == '':
                return None

            products = self.df[self.df["Артикул"] == article.strip()]
            if products.empty:
                return None

            # Беремо базову інформацію з першого запису
            first_product = products.iloc[0]
            name = first_product["Номенклатура"].split("(")[0].strip()
            price = float(first_product["Ціна"])
            # Штрихкод може бути різним для специфікацій, тому його краще брати з конкретного рядка нижче

            specifications = []
            for _, row in products.iterrows():
                spec_index = row["Номенклатура"].find("(")
                spec_name = row["Номенклатура"][spec_index:].strip() if spec_index != -1 else ""
                specifications.append({
                    "specification": spec_name.rstrip(")"),
                    "quantity": int(row["Кількість\n(залишок)"]),
                    "price": float(row["Ціна"]),
                    "barcode": str(row["Штрихкод"])  # Додаємо штрихкод
                })
            return {
                "name": name,
                "article": article,
                "price": price,  # Базова ціна
                "specifications": specifications,
            }
        except Exception as e:
            print(f"Помилка при отриманні деталей товару: {e}")
            return None

    async def get_product_info(self, article: str) -> Optional[Tuple[str, float, int]]:
        """
        Отримати інформацію про товар за артикулом.
        Ця функція використовується для внутрішніх операцій, як-от додавання до кошика,
        і повертає тільки 3 основні значення.
        """
        if not await self._load_data() or self.df is None:
            return None

        try:
            if not article or article.strip() == '':
                return None

            product = self.df[self.df["Артикул"] == article.strip()]
            if product.empty:
                return None

            # Беремо перший запис, якщо є кілька специфікацій
            first_row = product.iloc[0]
            name = first_row["Номенклатура"]
            price = float(first_row["Ціна"])
            quantity = int(first_row["Кількість\n(залишок)"])

            # Повертаємо кортеж з 3 елементів, як і очікує код
            return (name, price, quantity)

        except Exception as e:
            print(f"Помилка при отриманні інформації про товар за артикулом: {e}")
            return None

    async def is_available(self, article: str) -> bool:
        """
        Перевірити наявність товару на складі.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return False
        # Індекс 2 відповідає кількості (quantity)
        return product_info[2] > 0

    async def get_price(self, article: str) -> Optional[float]:
        """
        Отримати ціну товару за артикулом.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return None
        # Індекс 1 відповідає ціні (price)
        return product_info[1]

    async def get_name(self, article: str) -> Optional[str]:
        """
        Отримати назву товару за артикулом.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return None
        # Індекс 0 відповідає назві (name)
        return product_info[0]

    async def get_barcode(self, article: str) -> Optional[str]:
        """
        Отримати штрихкод товару за артикулом.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return None
        # Індекс 3 відповідає штрихкоду (barcode)
        return product_info[3]

    async def get_barcodes_by_article(self, article: str) -> Optional[List[Tuple[str, str]]]:
        """
        Отримати всі штрих-коди та номенклатури для зазначеного артикулу.
        Повертає список кортежів [(штрих-код, номенклатура), ...].
        """
        if not await self._load_data() or self.df is None:
            return None
        try:
            if not article or not str(article).strip():
                return None

            # Фільтруємо DataFrame за артикулом
            products = self.df[self.df["Артикул"] == str(article).strip()]
            if products.empty:
                return None

            # Витягуємо штрих-коди та номенклатури
            barcodes_info = []
            for _, row in products.iterrows():
                barcode = str(row["Штрихкод"])
                name = str(row["Номенклатура"])
                # Переконуємося, що значення не порожні та валідні
                if barcode and name and barcode != 'nan':
                    barcodes_info.append((barcode, name))

            return barcodes_info if barcodes_info else None
        except Exception as e:
            print(f"Помилка під час отримання штрих-кодів за артикулом: {e}")
            return None
