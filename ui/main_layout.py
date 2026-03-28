from nicegui import ui, app
from datetime import datetime
from core.state import clock_state

from .tab_dashboard import build_dashboard_tab
from .tab_schedule import build_schedule_tab
from .tab_calibration import build_calibration_tab
from .tab_settings import build_settings_tab
from .tab_user import build_users_tab


def create_layout():
    """Створює головну оболонку веб-застосунку з навігацією"""
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
    # Запускаємо таймер, який щосекунди оновлює глобальний годинник для цього клієнта
    ui.timer(1.0, lambda: setattr(clock_state, 'time_str', datetime.now().strftime("%H:%M:%S")))

    ui.colors(
        primary='#1c396e',  # Основний темно-синій КПІ
        secondary='#1062a3',  # Додатковий синій
        accent='#f07d00',  # Помаранчевий
        negative='#7f0d38',  # Бордовий (для помилок/видалення)
        warning='#ec6605',  # Темно-помаранчевий
        positive='#21ba45',  # Залишимо стандартний зелений для успішних дій (у брендбуці немає чистого зеленого)
        info='#008acf'  # Блакитний для інформації
    )
    def logout():
        app.storage.user['authenticated'] = False
        app.storage.user.clear()  # Повністю очищаємо дані сесії
        ui.navigate.to('/login')

    current_role = app.storage.user.get('role', 'operator')
    current_user = app.storage.user.get('username', 'Гість')
    is_admin = current_role == 'admin'

    with ui.header().classes('row items-center justify-between px-4 py-4 shadow-md bg-primary'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('schedule', size='md', color='white')
            ui.label('Годинникова вежа КПІ ім. Ігоря Сікорського').classes('text-h5 font-bold text-white')

        # Кнопка виходу в правому куті
        with ui.row().classes('items-center gap-4'):
            role_badge = 'Адміністратор' if is_admin else 'Оператор'
            ui.label(f"{role_badge} {current_user}").classes('text-sm font-medium opacity-90')
            ui.button(icon='logout', on_click=logout).props('flat round color=white').tooltip('Вийти з системи')

    with ui.tabs().classes('w-full bg-gray-200 text-primary shadow-sm') as tabs:
        tab_dash = ui.tab('Дашборд', icon='dashboard')
        tab_sched = ui.tab('Розклад', icon='list_alt')
        tab_calib = ui.tab('Калібрування', icon='build')
        if is_admin:
            tab_set = ui.tab('Налаштування', icon='settings')
            tab_users = ui.tab('Користувачі', icon='person')

    with ui.tab_panels(tabs, value=tab_dash).classes('w-full max-w-5xl mx-auto mt-6 bg-transparent'):
        with ui.tab_panel(tab_dash):
            build_dashboard_tab()

        with ui.tab_panel(tab_sched):
            build_schedule_tab()

        with ui.tab_panel(tab_calib):
            build_calibration_tab()
        if is_admin:
            with ui.tab_panel(tab_set):
                build_settings_tab()
            with ui.tab_panel(tab_users):
                build_users_tab()

    with ui.footer().classes(
            'bg-white border-t border-gray-200 p-2 justify-center shadow-[0_-1px_3px_rgba(0,0,0,0.05)]'):
        with ui.row().classes('items-center gap-2'):
            ui.label('Виробничий центр "Ядро" | КПІ ім. Ігоря Сікорського').classes('text-xs text-gray-500 font-medium')