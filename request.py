import hashlib
import secrets
import asyncpg

from db import db_instance

SECRET_KEY = '8fa0f1b045a6337d95427211ba8d719c05a5e157b7ee705a948aaf8356d6524e'

def generate_secret_key(length=32):
    return secrets.token_hex(length)

def hash_data(data):
    new_data = data + SECRET_KEY
    return hashlib.sha256(new_data.encode()).hexdigest()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def add_user(username: str, password: str, is_admin: bool = False):
    if not username or not password:
        raise ValueError("Имя пользователя и пароль обязательны")
    
    try:
        pool = await db_instance.get_pool()
        hashed_password = hash_password(password)
        
        async with pool.acquire() as conn:
            try:
                print(f"Попытка добавить пользователя: {username}")
                await conn.execute(
                    'INSERT INTO users (username, password, is_admin) VALUES ($1, $2, $3)',
                    username, hashed_password, is_admin
                )
                print(f"Пользователь {username} успешно добавлен")
            except asyncpg.UniqueViolationError:
                print(f"Пользователь {username} уже существует")
                raise ValueError(f"Пользователь {username} уже существует")
            except Exception as e:
                print(f"Ошибка при добавлении пользователя в БД: {str(e)}")
                raise ValueError(f"Ошибка при добавлении пользователя: {str(e)}")
    except Exception as e:
        print(f"Ошибка при подключении к БД: {str(e)}")
        raise ValueError(f"Ошибка подключения к базе данных: {str(e)}")

async def user_exists(username: str) -> bool:
    if not username:
        return False
    
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchval('SELECT id FROM users WHERE username = $1', username)
            return result is not None
        except Exception as e:
            print(f"Ошибка при проверке существования пользователя: {e}")
            raise e

async def authenticate_user(username: str, password: str):
    if not username or not password:
        return None
    
    pool = await db_instance.get_pool()
    hashed_password = hash_password(password)
    
    async with pool.acquire() as conn:
        try:
            user = await conn.fetchrow(
                'SELECT id, username, is_admin FROM users WHERE username = $1 AND password = $2',
                username, hashed_password
            )
            return user
        except Exception as e:
            print(f"Ошибка при аутентификации пользователя: {e}")
            raise e

async def add_book(title: str, author_id: int, genre: str, description: str, quantity: int):
    if not title or not author_id:
        raise ValueError("Название книги и ID автора обязательны")
    
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                '''INSERT INTO books (title, author_id, genre, description, quantity, available_quantity)
                   VALUES ($1, $2, $3, $4, $5, $5)''',
                title, author_id, genre, description, quantity
            )
        except Exception as e:
            print(f"Ошибка при добавлении книги: {e}")
            raise e

async def update_book(book_id, title, author_id, genre, description, quantity):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            '''UPDATE books SET title = $1, author_id = $2, genre = $3, 
               description = $4, quantity = $5 WHERE id = $6''',
            title, author_id, genre, description, quantity, book_id
        )

async def get_all_books():
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            return await conn.fetch(
                '''SELECT b.*, a.name as author_name FROM books b 
                   LEFT JOIN authors a ON b.author_id = a.id'''
            )
        except Exception as e:
            print(f"Ошибка при получении списка книг: {e}")
            raise e

async def get_book(book_id: int):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            return await conn.fetchrow(
                '''SELECT b.*, a.name as author_name FROM books b 
                   LEFT JOIN authors a ON b.author_id = a.id WHERE b.id = $1''',
                book_id
            )
        except Exception as e:
            print(f"Ошибка при получении информации о книге: {e}")
            raise e

async def add_author(name: str, biography: str = None):
    if not name:
        raise ValueError("Имя автора обязательно")
    
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                'INSERT INTO authors (name, biography) VALUES ($1, $2)',
                name, biography
            )
        except Exception as e:
            print(f"Ошибка при добавлении автора: {e}")
            raise e

async def get_all_authors():
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            return await conn.fetch('SELECT * FROM authors')
        except Exception as e:
            print(f"��шибка при получении списка авторов: {e}")
            raise e

async def get_author(author_id: int):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            return await conn.fetchrow('SELECT * FROM authors WHERE id = $1', author_id)
        except Exception as e:
            print(f"Ошибка при получении информации об авторе: {e}")
            raise e

async def borrow_book(book_id: int, user_id: int) -> bool:
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            book = await conn.fetchrow(
                'SELECT available_quantity FROM books WHERE id = $1',
                book_id
            )
            if book and book['available_quantity'] > 0:
                async with conn.transaction():
                    await conn.execute(
                        'UPDATE books SET available_quantity = available_quantity - 1 WHERE id = $1',
                        book_id
                    )
                    await conn.execute(
                        '''INSERT INTO book_loans (book_id, user_id, loan_date)
                           VALUES ($1, $2, CURRENT_TIMESTAMP)''',
                        book_id, user_id
                    )
                    return True
            return False
        except Exception as e:
            print(f"Ошибка при попытке взять книгу: {e}")
            raise e

async def return_book(book_id: int, user_id: int):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                await conn.execute(
                    '''UPDATE book_loans SET is_returned = TRUE, return_date = CURRENT_TIMESTAMP
                       WHERE book_id = $1 AND user_id = $2 AND is_returned = FALSE''',
                    book_id, user_id
                )
                await conn.execute(
                    'UPDATE books SET available_quantity = available_quantity + 1 WHERE id = $1',
                    book_id
                )
        except Exception as e:
            print(f"Ошибка при возврате книги: {e}")
            raise e
