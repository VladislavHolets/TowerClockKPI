from nicegui import ui, app
from database.crud import verify_user


def build_login_page():
    # Робимо гарний фон на весь екран та підключаємо шрифти
    ui.add_head_html('''
        <style>
            /* Звичайний шрифт (Regular) */
            @font-face {
                font-family: 'Exo 2';
                src: url('/static/fonts/Exo2-Regular.ttf') format('truetype');
                font-weight: 400;
                font-style: normal;
            }

            /* Напівжирний шрифт (SemiBold) */
            @font-face {
                font-family: 'Exo 2';
                src: url('/static/fonts/Exo2-SemiBold.ttf') format('truetype');
                font-weight: 600;
                font-style: normal;
            }

            /* Застосовуємо шрифт Exo 2 до всіх елементів тексту */
            body, .nicegui-content, .q-tab__label, .q-btn__content, .q-input, 
            .text-h5, .text-h6, .text-subtitle1, .text-subtitle2 {
                font-family: 'Exo 2', sans-serif !important;
            }

            /* ПРИМУСОВО переводимо всі "жирні" класи на SemiBold (600), як вимагає брендбук */
            b, strong, .font-bold, .text-bold {
                font-weight: 600 !important;
            }
        </style>
    ''')

    ui.colors(
        primary='#1c396e',  # Основний темно-синій КПІ
        secondary='#1062a3',  # Додатковий синій
        accent='#f07d00',  # Помаранчевий
        negative='#7f0d38',  # Бордовий (для помилок/видалення)
        warning='#ec6605',  # Темно-помаранчевий
        positive='#21ba45',  # Стандартний зелений для успішних дій
        info='#008acf'  # Блакитний для інформації
    )

    with ui.column().classes('w-full h-screen items-center justify-center bg-gray-100 relative'):

        with ui.card().classes('w-96 p-8 shadow-2xl items-center rounded-xl border-t-4 border-primary'):
            ui.icon('schedule', size='4rem').classes('text-primary mb-2')

            ui.label('Годинникова вежа КПІ').classes('text-h5 font-bold text-gray-800 text-center')
            ui.label('Вхід у систему').classes('text-subtitle1 text-gray-500 mb-8')

            username = ui.input('Логін').classes('w-full mb-4').props('autofocus')
            password = ui.input('Пароль', password=True, password_toggle_button=True).classes('w-full mb-8')

            def try_login():
                user_obj = verify_user(username.value, password.value)
                if user_obj:
                    app.storage.user['authenticated'] = True
                    app.storage.user['username'] = user_obj.username
                    app.storage.user['role'] = getattr(user_obj, 'role', 'operator')
                    ui.notify('Успішний вхід!', type='positive')
                    ui.navigate.to('/')
                else:
                    ui.notify('Невірний логін або пароль!', type='negative')
                    password.value = ''

            # === МАГІЯ ENTER ===
            # Прив'язуємо натискання клавіші Enter у будь-якому з полів до функції try_login
            username.on('keydown.enter', try_login)
            password.on('keydown.enter', try_login)

            ui.button('УВІЙТИ', on_click=try_login).classes('w-full bg-primary text-white shadow-md py-3 font-bold')

        # Акуратний футер
        with ui.row().classes('absolute bottom-6 w-full justify-center'):
            ui.label('Розроблено у Виробничому центрі «Ядро»').classes(
                'text-sm text-gray-400 font-semibold tracking-wide')