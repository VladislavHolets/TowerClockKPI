from nicegui import ui
from database.crud import get_system_settings, engine
from sqlmodel import Session


def save_settings(settings_obj):
    with Session(engine) as session:
        # Використовуємо merge() замість add().
        # Це копіює дані в базу, але залишає сам об'єкт живим для інтерфейсу NiceGUI.
        session.merge(settings_obj)
        session.commit()
    ui.notify('Налаштування механіки збережено!', type='positive')

def build_settings_tab():
    ui.label('Глобальні налаштування системи').classes('text-h6 mb-4')

    settings = get_system_settings()

    if not settings:
        ui.label('Помилка завантаження налаштувань.').classes('text-red-500')
        return

    with ui.card().classes('w-full max-w-3xl p-6'):
        ui.label('⚙️ Налаштування механіки (Шестерні)').classes('text-subtitle1 font-bold mb-2')
        ui.label(
            'Ці параметри дозволяють легко підлаштувати програму під будь-який редуктор чи розмір циферблата.').classes(
            'text-caption text-gray-500 mb-6')

        # 1. Передаточне число
        with ui.row().classes('w-full items-center mb-6'):
            ui.label('Кроків на 1 хвилину:').classes('w-1/3 font-medium text-gray-700')
            ui.number(value=125).bind_value(settings, 'steps_per_minute_dial').classes('w-1/4')
            ui.label('(Якщо 1 год = 7500 кроків, то 1 хв = 125)').classes('w-1/3 text-xs text-gray-400 ml-4')

        ui.separator().classes('mb-6')
        ui.label('Швидкість руху стрілок').classes('font-bold text-gray-700 mb-4')

        # 2. Швидкість звичайного ходу
        with ui.row().classes('w-full items-center mb-6'):
            ui.label('Звичайний крок триває:').classes('w-1/3 font-medium text-gray-700')
            ui.slider(min=0.5, max=60.0, step=0.5).bind_value(settings, 'normal_move_sec').classes('w-1/3')
            ui.number(suffix=' сек').bind_value(settings, 'normal_move_sec').classes('w-1/5 ml-4')

        # 3. Швидкість калібрування
        with ui.row().classes('w-full items-center mb-8'):
            ui.label('Крок калібрування триває:').classes('w-1/3 font-medium text-gray-700')
            ui.slider(min=0.05, max=2.0, step=0.05).bind_value(settings, 'fast_move_sec').classes(
                'w-1/3 text-orange-500')
            ui.number(suffix=' сек').bind_value(settings, 'fast_move_sec').classes('w-1/5 ml-4')

        ui.button('Зберегти параметри механіки', on_click=lambda: save_settings(settings), icon='save').classes(
            'w-full bg-green-600 shadow-md')