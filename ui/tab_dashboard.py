import threading
from nicegui import ui
from datetime import datetime
from core.state import clock_state
from core.scheduler import scheduler
from hardware.motor import step_motor
from hardware.audio import is_quiet_time, play_test_audio, stop_audio

def trigger_test_audio():
    ui.notify('Запуск тестового аудіо (Гонг)...', type='info')
    threading.Thread(target=play_test_audio, daemon=True).start()


def trigger_stop_audio():
    ui.notify('Примусова зупинка аудіо!', type='warning')
    stop_audio()


def build_dashboard_tab():
    """Будує інтерфейс головної вкладки (Дашборд)"""

    with ui.column().classes('w-full items-center pt-2'):

        # 1. ВЕЛИКИЙ ЦИФРОВИЙ ГОДИННИК
        clock_label = ui.label().bind_text_from(clock_state, 'time_str').classes(
            'text-5xl font-mono font-bold text-primary mt-2 mb-2 shadow-sm rounded px-6 py-2 bg-white border'
        )
        date_label = ui.label(datetime.now().strftime('%d.%m.%Y')).classes('text-xl text-gray-500 mb-8 font-medium')
        # Таймер для оновлення дати (раз на хвилину)
        ui.timer(60.0, lambda: date_label.set_text(datetime.now().strftime('%d.%m.%Y')))

        with ui.row().classes('w-full max-w-5xl justify-center gap-6 items-stretch'):

            # 2. КАРТКА СТАТУСУ ТА РОЗКЛАДУ
            with ui.card().classes('w-96 p-6 shadow-md flex flex-col'):
                ui.label('Статус системи').classes('text-h6 font-bold mb-4')

                # Поточний режим (Тиша чи Активно)
                status_row = ui.row().classes('items-center mb-4')
                status_icon = ui.icon('volume_up', size='sm')
                status_text = ui.label('Аудіосистема активна').classes('font-medium')

                def update_status():
                    if is_quiet_time():
                        status_icon.name = 'mode_night'
                        status_icon.classes(replace='text-orange-500')
                        status_text.set_text('Діє період тиші (звук вимкнено)')
                    else:
                        status_icon.name = 'volume_up'
                        status_icon.classes(replace='text-green-600')
                        status_text.set_text('Аудіосистема активна')

                update_status()
                ui.timer(60.0, update_status)

                ui.separator().classes('mb-4')

                # Інформація про наступну подію
                ui.label('Наступна аудіо подія:').classes('text-sm text-gray-500 mb-1')
                next_event_time = ui.label('--:--').classes('text-2xl font-bold text-gray-800')
                next_event_name = ui.label('Обчислення...').classes('text-md text-gray-600')

                def update_next_event():
                    jobs = scheduler.get_jobs()
                    audio_jobs = [j for j in jobs if j.id.startswith('event_') and j.next_run_time]

                    if audio_jobs:
                        next_job = min(audio_jobs, key=lambda j: j.next_run_time)
                        local_time = next_job.next_run_time.astimezone()
                        time_str = local_time.strftime('%H:%M')

                        if local_time.date() != datetime.now().date():
                            time_str = f"{time_str} ({local_time.strftime('%d.%m')})"

                        event_title = next_job.args[0] if next_job.args else "Мелодія"
                        next_event_time.set_text(time_str)
                        next_event_name.set_text(event_title)
                    else:
                        next_event_time.set_text('--:--')
                        next_event_name.set_text('Немає активних подій')

                update_next_event()
                ui.timer(10.0, update_next_event)

                # БЛОК АУДІО КНОПОК
                ui.space()  # Відштовхуємо кнопки в самий низ картки
                ui.separator().classes('mb-4 mt-2')
                with ui.row().classes('w-full gap-2'):
                    ui.button('Тест', icon='play_circle', color='secondary', on_click=trigger_test_audio).classes(
                        'flex-1')
                    ui.button('Зупинити', icon='stop', color='negative', on_click=trigger_stop_audio).classes('flex-1')

            # 3. КАРТКА КЕРУВАННЯ МЕХАНІКОЮ
            with ui.card().classes('w-96 p-6 shadow-md'):
                ui.label('Швидка механіка').classes('text-h6 font-bold mb-2')
                ui.label('Ручне коригування часу на циферблаті без запуску процесу калібрування.').classes(
                    'text-xs text-gray-500 mb-6')

                with ui.column().classes('w-full gap-4'):
                    # Рух ВПЕРЕД
                    with ui.row().classes(
                            'w-full justify-between items-center bg-gray-100 p-2 rounded border border-gray-300'):
                        ui.label('Вперед:').classes('font-medium text-sm text-primary')
                        with ui.row().classes('gap-2'):
                            ui.button('+1 хв', on_click=lambda: step_motor(1), color='primary').props('size=sm')
                            ui.button('+5 хв', on_click=lambda: step_motor(5), color='primary').props('size=sm')

                    # Рух НАЗАД
                    with ui.row().classes(
                            'w-full justify-between items-center bg-gray-100 p-2 rounded border border-gray-300 mt-2'):
                        ui.label('Назад:').classes('font-medium text-sm text-accent')
                        with ui.row().classes('gap-2'):
                            ui.button('-1 хв', on_click=lambda: step_motor(-1), color='warning').props('size=sm')
                            ui.button('-5 хв', on_click=lambda: step_motor(-5), color='warning').props('size=sm')