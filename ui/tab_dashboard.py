from nicegui import ui
from datetime import datetime
from core.state import clock_state

def build_dashboard_tab():
    """Будує інтерфейс головної вкладки (Дашборд)"""

    with ui.row().classes('w-full justify-between items-stretch gap-4'):
        # 1. Картка поточного часу
        with ui.card().classes('flex-1 text-center items-center p-6'):
            ui.label('Точний час сервера (NTP)').classes('text-subtitle1 text-gray-500')
            time_label = ui.label().classes('text-h2 font-mono text-blue-600 mt-4')
            # Таймер, який оновлює текст кожну секунду
            ui.label().bind_text_from(clock_state, 'time_str').classes('text-h2 font-mono text-blue-600 mt-4')
        # 2. Картка статусу системи
        with ui.card().classes('flex-1 text-center items-center p-6'):
            ui.label('Статус системи').classes('text-subtitle1 text-gray-500')

            with ui.column().classes('mt-4 gap-2 items-center'):
                ui.label('Механіка: АКТИВНА (Тік щохвилини)').classes('text-green-600 font-bold')
                ui.label('Аудіо: ОЧІКУВАННЯ РОЗКЛАДУ').classes('text-orange-600 font-bold')

            ui.button('ЕКСТРЕНА ЗУПИНКА', color='red', icon='stop_circle').classes('mt-6 w-full')