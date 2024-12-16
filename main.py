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

from db import db_instance
from request import (add_user, user_exists, authenticate_user, add_book, 
                    get_all_books, get_book, add_author, get_all_authors,
                    get_author, borrow_book, return_book)

class LoginScreen(Screen):
    def login(self):
        app = App.get_running_app()
        username = self.ids.username_input.text
        password = self.ids.password_input.text
        
        def callback(future):
            user = future.result()
            if user:
                app.current_user = user
                if user['is_admin']:
                    self.manager.current = 'admin_panel'
                else:
                    self.manager.current = 'library_main'
            else:
                self.ids.error_label.text = 'Неверный логин или пароль'
        
        future = app.loop.create_task(authenticate_user(username, password))
        future.add_done_callback(callback)

class RegistrationScreen(Screen):
    def register(self):
        asyncio.create_task(self._register())

    async def _register(self):
        username = self.ids.username_input.text
        password = self.ids.password_input.text
        is_admin = self.ids.admin_checkbox.active
        
        if await user_exists(username):
            self.ids.error_label.text = 'Пользователь с таким логином уже существует!'
        else:
            await add_user(username, password, is_admin)
            self.manager.current = 'login'

class LibraryMainScreen(Screen):
    def on_enter(self):
        asyncio.create_task(self._load_books())

    async def _load_books(self):
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

    def show_book_details(self, instance):
        App.get_running_app().book_id = instance.book_id
        self.manager.current = 'book_details'

class BookDetailsScreen(Screen):
    def on_enter(self):
        asyncio.create_task(self._load_book_details())

    async def _load_book_details(self):
        book_id = App.get_running_app().book_id
        book = await get_book(book_id)
        self.ids.title_label.text = f'Название: {book["title"]}'
        self.ids.author_label.text = f'Автор: {book["author_name"]}'
        self.ids.genre_label.text = f'Жанр: {book["genre"]}'
        self.ids.description_label.text = f'Описание: {book["description"]}'
        self.ids.available_label.text = f'Доступно: {book["available_quantity"]}'

    def borrow_book(self):
        asyncio.create_task(self._borrow_book())

    async def _borrow_book(self):
        book_id = App.get_running_app().book_id
        user_id = App.get_running_app().current_user['id']
        if await borrow_book(book_id, user_id):
            self.ids.status_label.text = 'Книга успешно взята'
            await self._load_book_details()
        else:
            self.ids.status_label.text = 'Книга недоступна'

class AdminPanelScreen(Screen):
    def add_book(self):
        asyncio.create_task(self._add_book())

    async def _add_book(self):
        title = self.ids.book_title_input.text
        author_id = int(self.ids.author_id_input.text)
        genre = self.ids.genre_input.text
        description = self.ids.description_input.text
        quantity = int(self.ids.quantity_input.text)
        
        await add_book(title, author_id, genre, description, quantity)
        self.ids.status_label.text = 'Книга успешно добавлена'

    def add_author(self):
        asyncio.create_task(self._add_author())

    async def _add_author(self):
        name = self.ids.author_name_input.text
        biography = self.ids.author_bio_input.text
        
        await add_author(name, biography)
        self.ids.status_label.text = 'Автор успешно добавлен'

class MainApp(App):
    def build(self):
        self.current_user = None
        self.book_id = None
        self.loop = asyncio.get_event_loop()
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegistrationScreen(name='registration'))
        sm.add_widget(LibraryMainScreen(name='library_main'))
        sm.add_widget(BookDetailsScreen(name='book_details'))
        sm.add_widget(AdminPanelScreen(name='admin_panel'))
        return sm

if __name__ == "__main__":
    MainApp().run()