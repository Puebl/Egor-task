from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import asyncio
import sys

from db import db_instance
from request import (add_user, user_exists, authenticate_user, add_book, 
                    get_all_books, get_book, add_author, get_all_authors,
                    get_author, borrow_book, return_book)

class LoginScreen(Screen):
    def login(self):
        print("Начало входа")
        app = App.get_running_app()
        username = self.ids.username_input.text
        password = self.ids.password_input.text
        
        async def do_login():
            try:
                print(f"Попытка входа для пользователя: {username}")
                user = await authenticate_user(username, password)
                if user:
                    print("Вход успешен")
                    app.current_user = user
                    app.loop.call_soon_threadsafe(self.switch_to_main)
                else:
                    print("Неверные учетные данные")
                    app.loop.call_soon_threadsafe(lambda: self.show_error('Неверный логин или пароль'))
            except Exception as e:
                print(f"Ошибка при входе: {str(e)}")
                app.loop.call_soon_threadsafe(lambda: self.show_error(str(e)))

        future = app.loop.create_task(do_login())
        future.add_done_callback(lambda f: print("Процесс входа завершен"))

    def switch_to_main(self):
        if App.get_running_app().current_user['is_admin']:
            self.manager.current = 'admin_panel'
        else:
            self.manager.current = 'library_main'

    def show_error(self, error_msg):
        self.ids.error_label.text = error_msg

class RegistrationScreen(Screen):
    def register(self):
        print("Начало регистрации")
        app = App.get_running_app()
        username = self.ids.username_input.text
        password = self.ids.password_input.text
        is_admin = self.ids.admin_checkbox.active
        
        print(f"Данные для регистрации: username={username}, is_admin={is_admin}")
        
        async def register_user():
            print("Начало асинхронной регистрации")
            try:
                if not username or not password:
                    print("Пустые поля")
                    app.loop.call_soon_threadsafe(lambda: self.show_error('Заполните все поля'))
                    return
                
                exists = await user_exists(username)
                print(f"Проверка существ��вания пользователя: {exists}")
                
                if exists:
                    print("Пользователь уже существует")
                    app.loop.call_soon_threadsafe(lambda: self.show_error('Пользователь с таким логином уже существует!'))
                else:
                    print("Добавление нового пользователя")
                    await add_user(username, password, is_admin)
                    print("Пользователь добавлен успешно")
                    # После регистрации авторизуем пользователя
                    user = await authenticate_user(username, password)
                    if user:
                        print("Автоматическая авторизация успешна")
                        app.current_user = user
                        app.loop.call_soon_threadsafe(self.switch_to_main)
                    else:
                        print("Ошибка автоматической авторизации")
                        raise ValueError("Ошибка автоматической авторизации")
            except Exception as e:
                print(f"Ошибка при регис��рации: {str(e)}")
                error_msg = str(e)
                app.loop.call_soon_threadsafe(lambda: self.show_error(error_msg))

        try:
            print("Создание задачи регистрации")
            future = app.loop.create_task(register_user())
            print("Задача регистрации создана")
        except Exception as e:
            print(f"Ошибка при создании задачи: {str(e)}")
            self.show_error(f"Системная ошибка: {str(e)}")

    def switch_to_main(self):
        print("Переключение на главный экран")
        if App.get_running_app().current_user['is_admin']:
            print("Переход на панель администратора")
            self.manager.current = 'admin_panel'
        else:
            print("Переход на экран библиотеки")
            self.manager.current = 'library_main'

    def show_error(self, error_msg):
        print(f"Отображение ошибки: {error_msg}")
        self.ids.error_label.text = f'Ошибка: {error_msg}'

class LibraryMainScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        async def load_books():
            try:
                books = await get_all_books()
                self.ids.books_grid.clear_widgets()
                for book in books:
                    book_widget = BoxLayout(orientation='vertical', size_hint_y=None, height=100)
                    book_widget.add_widget(Label(text=f'Название: {book["title"]}'))
                    book_widget.add_widget(Label(text=f'Автор: {book["author_name"]}'))
                    book_widget.add_widget(Label(text=f'Доступно: {book["available_quantity"]}'))
                    details_btn = Button(text='Подробнее')
                    details_btn.book_id = book['id']
                    details_btn.bind(on_press=self.show_book_details)
                    book_widget.add_widget(details_btn)
                    self.ids.books_grid.add_widget(book_widget)
            except Exception as e:
                print(f'Ошибка загрузки книг: {str(e)}')
        
        future = app.loop.create_task(load_books())

    def show_book_details(self, instance):
        App.get_running_app().book_id = instance.book_id
        self.manager.current = 'book_details'

class BookDetailsScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        async def load_details():
            try:
                book_id = app.book_id
                book = await get_book(book_id)
                self.ids.title_label.text = f'Название: {book["title"]}'
                self.ids.author_label.text = f'Автор: {book["author_name"]}'
                self.ids.genre_label.text = f'Жанр: {book["genre"]}'
                self.ids.description_label.text = f'Описание: {book["description"]}'
                self.ids.available_label.text = f'Доступно: {book["available_quantity"]}'
            except Exception as e:
                print(f'Ошибка загрузки деталей книги: {str(e)}')
        
        future = app.loop.create_task(load_details())

    def borrow_book(self):
        app = App.get_running_app()
        async def do_borrow():
            try:
                book_id = app.book_id
                user_id = app.current_user['id']
                if await borrow_book(book_id, user_id):
                    self.ids.status_label.text = 'Книга успешно взята'
                    book = await get_book(book_id)
                    self.ids.available_label.text = f'Доступно: {book["available_quantity"]}'
                else:
                    self.ids.status_label.text = 'Книга недоступна'
            except Exception as e:
                self.ids.status_label.text = f'Ошибка: {str(e)}'
        
        future = app.loop.create_task(do_borrow())

class AdminPanelScreen(Screen):
    def add_book(self):
        app = App.get_running_app()
        async def do_add_book():
            try:
                title = self.ids.book_title_input.text
                author_id = int(self.ids.author_id_input.text)
                genre = self.ids.genre_input.text
                description = self.ids.description_input.text
                quantity = int(self.ids.quantity_input.text)
                
                await add_book(title, author_id, genre, description, quantity)
                self.ids.status_label.text = 'Книга успешно добавлена'
            except Exception as e:
                self.ids.status_label.text = f'Ошибка: {str(e)}'
        
        future = app.loop.create_task(do_add_book())

    def add_author(self):
        app = App.get_running_app()
        async def do_add_author():
            try:
                name = self.ids.author_name_input.text
                biography = self.ids.author_bio_input.text
                
                await add_author(name, biography)
                self.ids.status_label.text = 'Автор успешно добавлен'
            except Exception as e:
                self.ids.status_label.text = f'Ошибка: {str(e)}'
        
        future = app.loop.create_task(do_add_author())

class MainApp(App):
    def build(self):
        print("Инициализация приложения")
        self.current_user = None
        self.book_id = None
        
        try:
            self.loop = asyncio.get_event_loop()
            print("Получен существующий event loop")
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            print("Создан новый event loop")
        
        async def init_db():
            print("Начало инициализации базы данных")
            try:
                await db_instance.create_pool()
                print("База данных успешно инициализирована")
                
                # Проверяем подключение, пытаясь выполнить простой запрос
                pool = await db_instance.get_pool()
                async with pool.acquire() as conn:
                    await conn.fetchval('SELECT 1')
                print("Подключение к базе данных проверено")
                
                return True
            except Exception as e:
                print(f"Ошибка при инициализации базы данных: {e}")
                print(f"Тип ошибки: {type(e).__name__}")
                return False
        
        print("Запуск инициализации базы данных")
        future = self.loop.create_task(init_db())
        try:
            self.loop.run_until_complete(future)
            if not future.result():
                print("Не удалось инициализировать базу данных")
                return None
        except Exception as e:
            print(f"Критическая ошибка при инициализации: {e}")
            return None
        
        print("Event loop и база данных готовы")
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegistrationScreen(name='registration'))
        sm.add_widget(LibraryMainScreen(name='library_main'))
        sm.add_widget(BookDetailsScreen(name='book_details'))
        sm.add_widget(AdminPanelScreen(name='admin_panel'))
        return sm

    def on_stop(self):
        async def close_db():
            await db_instance.close_pool()
        
        self.loop.run_until_complete(close_db())
        self.loop.close()

if __name__ == "__main__":
    print("Запуск приложения")
    try:
        print("Создание экземпляра приложения")
        app = MainApp()
        
        print("Проверка подключения к базе данных")
        async def test_db():
            try:
                pool = await db_instance.get_pool()
                async with pool.acquire() as conn:
                    result = await conn.fetchval('SELECT 1')
                    print("Подключение к базе данных успешно")
                    return True
            except Exception as e:
                print(f"Ошибка подключения к базе данных: {str(e)}")
                return False
        
        loop = asyncio.get_event_loop()
        if not loop.run_until_complete(test_db()):
            print("Не удалось подключиться к базе данных")
            input("Нажмите Enter для выхода...")
            sys.exit(1)
        
        print("Запуск главного цикла приложения")
        app.run()
    except Exception as e:
        print(f"Критическая ошибка при запуске приложения: {str(e)}")
        print("Детали ошибки:", e.__class__.__name__)
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")