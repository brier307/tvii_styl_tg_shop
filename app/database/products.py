import pandas as pd
from typing import Optional, Tuple, Dict, List
from pathlib import Path
import zipfile
import shutil
import asyncio
from config import PATH_TO_STOCK


class ProductManager:
    def __init__(self, file_path: str = PATH_TO_STOCK):
        """
        Ініціалізація менеджера продуктів.
        Args:
            file_path (str): шлях до Excel файлу з товарами.
                             За замовчуванням встановлено шлях для 1С.
        """
        self.file_path = Path(file_path)
        self.df = None

    def _repackage_and_load_sync(self):
        """
        Синхронний хелпер для перепакування та завантаження даних.
        Ця функція виконується в окремому потоці, щоб не блокувати бота.
        """
        # --- Логіка перепакування ---
        try:
            if not self.file_path.is_file():
                raise FileNotFoundError(f"Файл не знайдено: {self.file_path}")

            needs_repackaging = False
            with zipfile.ZipFile(self.file_path, 'r') as z_in:
                namelist = z_in.namelist()
                if 'xl/SharedStrings.xml' in namelist and 'xl/sharedStrings.xml' not in namelist:
                    needs_repackaging = True

            if needs_repackaging:
                temp_file_path = self.file_path.with_suffix(f'.repacked.xlsx')
                with zipfile.ZipFile(self.file_path, 'r') as z_in, \
                        zipfile.ZipFile(temp_file_path, 'w', zipfile.ZIP_DEFLATED) as z_out:
                    for item in z_in.infolist():
                        buffer = z_in.read(item.filename)
                        if item.filename == 'xl/SharedStrings.xml':
                            item.filename = 'xl/sharedStrings.xml'
                        z_out.writestr(item, buffer)
                # Безпечно замінюємо оригінальний файл
                shutil.move(temp_file_path, self.file_path)
        except (FileNotFoundError, zipfile.BadZipFile) as e:
            # Якщо файл відсутній, пошкоджений або заблокований, pandas все одно видасть помилку,
            # яку ми обробимо нижче.
            print(f"Попередження при спробі перепакування: {e}")
        except Exception as e:
            print(f"Неочікувана помилка під час перепакування файлу: {e}")

        # --- Логіка завантаження та очищення даних ---
        self.df = pd.read_excel(
            self.file_path,
            header=1,
            usecols=[
                "Номенклатура",
                "Артикул",
                "Кількість\n(залишок)",
                "Ціна"
            ]
        )
        self.df = self.df.dropna(subset=["Номенклатура"])
        self.df["Артикул"] = self.df["Артикул"].astype(str).str.strip()
        self.df.loc[self.df["Артикул"] == 'nan', "Артикул"] = ''
        self.df["Кількість\n(залишок)"] = pd.to_numeric(self.df["Кількість\n(залишок)"], errors='coerce').fillna(0)
        self.df["Ціна"] = pd.to_numeric(self.df["Ціна"], errors='coerce').fillna(0)

    async def _load_data(self) -> bool:
        """
        Асинхронно завантажує дані з Excel файлу, виконуючи синхронний
        блокуючий код в окремому потоці.
        """
        try:
            # Виконуємо важку операцію вводу-виводу в потоці
            await asyncio.to_thread(self._repackage_and_load_sync)
            return True
        except Exception as e:
            print(f"ПОМИЛКА при завантаженні та обробці файлу: {e}")
            self.df = None
            return False

    async def get_product_details(self, article: str) -> Optional[dict]:
        """
        Отримати детальну інформацію про товар, включаючи специфікації.
        """
        if not await self._load_data() or self.df is None:
            return None

        try:
            if not article or article.strip() == '':
                return None

            products = self.df[self.df["Артикул"] == article.strip()]
            if products.empty:
                return None

            name = products["Номенклатура"].iloc[0].split("(")[0].strip()
            price = float(products["Ціна"].iloc[0])

            specifications = []
            for _, row in products.iterrows():
                spec_index = row["Номенклатура"].find("(")
                spec_name = row["Номенклатура"][spec_index:].strip() if spec_index != -1 else ""
                specifications.append({
                    "specification": spec_name.rstrip(")"),
                    "quantity": int(row["Кількість\n(залишок)"]),
                    "price": float(row["Ціна"]),
                })
            return {
                "name": name,
                "article": article,
                "price": price,
                "specifications": specifications,
            }
        except Exception as e:
            print(f"Помилка при отриманні деталей товару: {e}")
            return None

    async def get_product_info(self, article: str) -> Optional[Tuple[str, float, int]]:
        """
        Отримати інформацію про товар за артикулом.
        """
        if not await self._load_data() or self.df is None:
            return None

        try:
            if not article or article.strip() == '':
                return None

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

    async def is_available(self, article: str) -> bool:
        """
        Перевірити наявність товару на складі.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return False
        return product_info[2] > 0

    async def get_price(self, article: str) -> Optional[float]:
        """
        Отримати ціну товару за артикулом.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return None
        return product_info[1]

    async def get_name(self, article: str) -> Optional[str]:
        """
        Отримати назву товару за артикулом.
        """
        product_info = await self.get_product_info(article)
        if product_info is None:
            return None
        return product_info[0]