from nicegui import ui
from datetime import datetime
from core.state import clock_state
from hardware.motor import step_motor

def calculate_and_sync(hands_time_str: str):
    """Математика синхронізації (Двостороння)"""
    if not hands_time_str:
        ui.notify('Введіть час!', type='negative')
        return

    try:
        hands_time = datetime.strptime(hands_time_str, "%H:%M").time()
        now = datetime.now()

        hands_minutes_total = (hands_time.hour % 12) * 60 + hands_time.minute
        ntp_minutes_total = (now.hour % 12) * 60 + now.minute
        diff = (ntp_minutes_total - hands_minutes_total) % 720

        if diff == 0:
            ui.notify('Годинник вже показує точний час! Калібрування не потрібне.', type='positive')
            return

        if diff <= 360:
            minutes_to_move = diff
            direction_text = "вперед"
        else:
            minutes_to_move = diff - 720
            direction_text = "назад"

        ui.notify(f'Найкоротший шлях: {abs(minutes_to_move)} хв {direction_text}. Запускаємо...', type='warning')
        step_motor(minutes_to_move)

    except ValueError:
        ui.notify(f'Помилка формату: {hands_time_str}. Очікується ГГ:ХХ', type='negative')


def build_calibration_tab():
    """Будує інтерфейс вкладки калібрування стрілок"""

    ui.label('Сервісне керування механікою').classes('text-h6 mb-4')

    # Глобальний годинник (безпечний від помилок таймера)
    with ui.row().classes('items-center gap-4 mb-6 p-4 bg-white rounded shadow-sm w-full justify-center border'):
        ui.label('Еталонний час сервера (NTP):').classes('text-gray-600 text-lg')
        # МАГІЯ ТУТ: Безпечна прив'язка (bind) до глобального стану замість ui.timer
        ui.label().bind_text_from(clock_state, 'time_str').classes('font-mono font-bold text-3xl text-primary')

    with ui.row().classes('w-full gap-6 items-stretch'):
        # 1. Відносне керування
        with ui.card().classes('flex-1 p-6'):
            ui.label('Ручне підведення (Відносне)').classes('text-subtitle1 font-bold mb-2')
            ui.label('Використовуйте для точного коригування положення стрілок.').classes(
                'text-caption text-gray-500 mb-6')

            with ui.row().classes('w-full gap-2 mb-6'):
                ui.button('+ 1 хв', on_click=lambda: step_motor(1)).classes('flex-1 bg-info')
                ui.button('+ 5 хв', on_click=lambda: step_motor(5)).classes('flex-1 bg-secondary')
                ui.button('+ 10 хв', on_click=lambda: step_motor(10)).classes('flex-1 bg-primary')

            ui.separator()

            with ui.row().classes('w-full items-center mt-6 gap-4'):
                custom_minutes = ui.number('Довільна кількість хвилин', value=15, format='%.0f').classes('flex-1')
                ui.button('Крутити', on_click=lambda: step_motor(int(custom_minutes.value))).classes('bg-green-600')

        # 2. Розумна синхронізація (Матеріал Циферблат)
        with ui.card().classes('flex-1 p-6 bg-gray-100 border border-secondary'):
            ui.label('Розумна синхронізація (Абсолютне)').classes('text-subtitle1 font-bold text-primary mb-2')
            ui.label('Введіть час, який зараз фізично показують стрілки.').classes('text-caption text-gray-700 mb-6')

            with ui.input('Час на стрілках (ГГ:ХХ)', value='12:00').classes(
                    'w-full text-xl mb-8 bg-white px-4 rounded shadow-sm') as time_picker_input:
                with ui.menu().classes('p-0') as time_menu:
                    ui.time().bind_value(time_picker_input)
                with time_picker_input.add_slot('append'):
                    ui.icon('access_time').classes('cursor-pointer text-primary').on('click', time_menu.open)

            ui.space()
            ui.button('РОЗРАХУВАТИ ТА СИНХРОНІЗУВАТИ', on_click=lambda: calculate_and_sync(time_picker_input.value),
                      icon='sync').classes('w-full bg-accent text-white font-bold py-3 shadow-md')