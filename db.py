import asyncpg
import asyncio
import sys

DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_NAME = 'library_db'
DB_HOST = '127.0.0.1'
DB_PORT = '5432'

class Database:
    def __init__(self):
        self._db_pool = None
        self._initialized = False

    async def create_pool(self):
        if self._db_pool is None:
            try:
                print(f"Подключение к базе данных: {DB_HOST}:{DB_PORT}")
                self._db_pool = await asyncpg.create_pool(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    host=DB_HOST,
                    port=DB_PORT,
                    min_size=2,
                    max_size=10,
                    command_timeout=60
                )
                if not self._initialized:
                    await self.initialize_tables()
                    self._initialized = True
            except asyncpg.InvalidCatalogNameError:
                print(f"База данных {DB_NAME} не существует, создаем...")
                try:
                    sys_conn = await asyncpg.connect(
                        user=DB_USER,
                        password=DB_PASSWORD,
                        database='postgres',
                        host=DB_HOST,
                        port=DB_PORT,
                        command_timeout=60
                    )
                    await sys_conn.execute(f'CREATE DATABASE {DB_NAME}')
                    await sys_conn.close()
                    
                    self._db_pool = await asyncpg.create_pool(
                        user=DB_USER,
                        password=DB_PASSWORD,
                        database=DB_NAME,
                        host=DB_HOST,
                        port=DB_PORT,
                        min_size=2,
                        max_size=10,
                        command_timeout=60
                    )
                    await self.initialize_tables()
                    self._initialized = True
                except Exception as e:
                    print(f"Ошибка при создании базы данных: {e}")
                    raise e
            except Exception as e:
                print(f"Ошибка при подключении к базе данных: {e}")
                print(f"Проверьте, что PostgreSQL запущен и доступен по адресу {DB_HOST}:{DB_PORT}")
                print(f"Проверьте правильность имени пользователя ({DB_USER}) и пароля")
                raise e

    async def initialize_tables(self):
        print("Начало инициализации таблиц")
        async with self._db_pool.acquire() as conn:
            print("Создание таблицы users...")
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE
                )
            ''')
            print("Таблица users создана")
            
            print("Создание таблицы authors...")
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS authors (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    biography TEXT
                )
            ''')
            print("Таблица authors создана")
            
            print("Создание таблицы books...")
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    author_id INTEGER REFERENCES authors(id),
                    genre VARCHAR(50),
                    description TEXT,
                    quantity INTEGER DEFAULT 1,
                    available_quantity INTEGER DEFAULT 1
                )
            ''')
            print("Таблица books создана")
            
            print("Создание таблицы book_loans...")
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS book_loans (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER REFERENCES books(id),
                    user_id INTEGER REFERENCES users(id),
                    loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    return_date TIMESTAMP,
                    is_returned BOOLEAN DEFAULT FALSE
                )
            ''')
            print("Таблица book_loans создана")
            print("Все таблицы успешно созданы")

    async def get_pool(self):
        if self._db_pool is None:
            await self.create_pool()
        return self._db_pool

    async def close_pool(self):
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None

db_instance = Database()
