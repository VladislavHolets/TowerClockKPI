from nicegui import ui
from datetime import datetime
from core.state import clock_state

from .tab_dashboard import build_dashboard_tab
from .tab_schedule import build_schedule_tab
from .tab_calibration import build_calibration_tab
from .tab_settings import build_settings_tab


def create_layout():
    """Створює головну оболонку веб-застосунку з навігацією"""

    # Запускаємо таймер, який щосекунди оновлює глобальний годинник для цього клієнта
    ui.timer(1.0, lambda: setattr(clock_state, 'time_str', datetime.now().strftime("%H:%M:%S")))

    ui.colors(primary='#1976d2', secondary='#26a69a', accent='#9c27b0')

    with ui.header().classes('row items-center justify-between px-4 py-2 shadow-md'):
        ui.label('YADRO | Годинник Головного Корпусу').classes('text-h6 font-bold')
        ui.icon('schedule', size='md')

    with ui.tabs().classes('w-full bg-blue-50 text-blue-900 shadow-sm') as tabs:
        tab_dash = ui.tab('Дашборд', icon='dashboard')
        tab_sched = ui.tab('Розклад', icon='list_alt')
        tab_calib = ui.tab('Калібрування', icon='build')
        tab_set = ui.tab('Налаштування', icon='settings')

    with ui.tab_panels(tabs, value=tab_dash).classes('w-full max-w-5xl mx-auto mt-6 bg-transparent'):
        with ui.tab_panel(tab_dash):
            build_dashboard_tab()

        with ui.tab_panel(tab_sched):
            build_schedule_tab()

        with ui.tab_panel(tab_calib):
            build_calibration_tab()

        with ui.tab_panel(tab_set):
            build_settings_tab()
