import asyncpg
import asyncio

DB_USER = 'postgres'
DB_PASSWORD = 'admin'
DB_NAME = 'postgres'
DB_HOST = 'localhost'
DB_PORT = '5432'

class Database:
    def __init__(self):
        self._db_pool = None

    async def create_pool(self):
        if self._db_pool is None:
            try:
                self._db_pool = await asyncpg.create_pool(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    host=DB_HOST,
                    port=DB_PORT,
                )
                await self.initialize_tables()
            except Exception as e:
                print(f"Ошибка при подключении к базе данных: {e}")
                raise e

    async def initialize_tables(self):
        async with self._db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS authors (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    biography TEXT
                )
            ''')
            
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

    async def get_pool(self):
        if self._db_pool is None:
            await self.create_pool()
        return self._db_pool

    async def close_pool(self):
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None

db_instance = Database()
