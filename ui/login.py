from nicegui import ui, app
from database.crud import verify_user

def build_login_page():
    # Робимо гарний фон на весь екран
    with ui.column().classes('w-full h-screen items-center justify-center bg-gray-100'):
        with ui.card().classes('w-96 p-8 shadow-2xl items-center rounded-xl'):
            ui.icon('lock_person', size='4rem').classes('text-blue-600 mb-4')
            ui.label('YADRO | Вхід у систему').classes('text-h5 font-bold mb-8 text-gray-800')

            username = ui.input('Логін').classes('w-full mb-4').props('autofocus')
            password = ui.input('Пароль', password=True, password_toggle_button=True).classes('w-full mb-8')

            def try_login():
                if verify_user(username.value, password.value):
                    # Записуємо в безпечну сесію браузера, що користувач авторизований
                    app.storage.user['authenticated'] = True
                    app.storage.user['username'] = username.value
                    ui.notify('Успішний вхід!', type='positive')
                    # Перекидаємо на головну сторінку годинника
                    ui.navigate.to('/')
                else:
                    ui.notify('Невірний логін або пароль!', type='negative')
                    password.value = ''

            ui.button('Увійти', on_click=try_login).classes('w-full bg-blue-600 text-white shadow-md py-3 font-bold')