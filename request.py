import hashlib
import secrets

from db import db_instance

SECRET_KEY = '8fa0f1b045a6337d95427211ba8d719c05a5e157b7ee705a948aaf8356d6524e'

def generate_secret_key(length=32):
    return secrets.token_hex(length)

def hash_data(data):
    new_data = data + SECRET_KEY
    return hashlib.sha256(new_data.encode()).hexdigest()

async def add_user(username, password, is_admin=False):
    pool = await db_instance.get_pool()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO users (username, password, is_admin) VALUES ($1, $2, $3)',
            username, hashed_password, is_admin
        )

async def user_exists(username):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval('SELECT id FROM users WHERE username = $1', username)
        return result is not None

async def authenticate_user(username, password):
    pool = await db_instance.get_pool()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            'SELECT id, username, is_admin FROM users WHERE username = $1 AND password = $2',
            username, hashed_password
        )
        return user

async def add_book(title, author_id, genre, description, quantity):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            '''INSERT INTO books (title, author_id, genre, description, quantity, available_quantity)
               VALUES ($1, $2, $3, $4, $5, $5)''',
            title, author_id, genre, description, quantity
        )

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
        return await conn.fetch(
            '''SELECT b.*, a.name as author_name FROM books b 
               LEFT JOIN authors a ON b.author_id = a.id'''
        )

async def get_book(book_id):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            '''SELECT b.*, a.name as author_name FROM books b 
               LEFT JOIN authors a ON b.author_id = a.id WHERE b.id = $1''',
            book_id
        )

async def add_author(name, biography):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO authors (name, biography) VALUES ($1, $2)',
            name, biography
        )

async def get_all_authors():
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT * FROM authors')

async def get_author(author_id):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM authors WHERE id = $1', author_id)

async def borrow_book(book_id, user_id):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
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

async def return_book(book_id, user_id):
    pool = await db_instance.get_pool()
    async with pool.acquire() as conn:
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
