from pathlib import Path
from nicegui import ui
from database.crud import get_all_events, add_audio_event, toggle_audio_event, delete_audio_event, update_audio_event
from core.scheduler import reload_jobs

current_edit_id = {"id": None}


def get_media_files():
    media_dir = Path("storage/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    valid_extensions = {'.mp3', '.wav', '.ogg'}
    files = [f.name for f in media_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]
    return files if files else ["Файли не знайдені"]


def build_schedule_tab():
    ui.label('Керування розкладом аудіо подій').classes('text-h6 mb-4')

    with ui.dialog() as upload_dialog, ui.card().classes('min-w-[400px]'):
        ui.label('Завантажити новий аудіофайл').classes('text-h6 font-bold')
        ui.label('Підтримуються формати: .mp3, .wav, .ogg').classes('text-caption text-gray-500 mb-2')

        async def handle_upload(e):
            media_dir = Path("storage/media")
            file_path = media_dir / e.file.name
            file_bytes = await e.file.read()
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            ui.notify(f'Файл "{e.file.name}" збережено!', type='positive')
            upload_dialog.close()

        ui.upload(on_upload=handle_upload, multiple=False, auto_upload=True, label="Перетягніть файл сюди").classes(
            'w-full')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Закрити', on_click=upload_dialog.close, color='gray')

    with ui.dialog() as dialog, ui.card().classes('min-w-[450px]'):
        dialog_title = ui.label('Додати нову подію').classes('text-h6 font-bold')

        name_input = ui.input('Назва (напр. 1 Вересня)').classes('w-full mb-2')

        ui.label('Як часто відтворювати?').classes('text-sm text-gray-600 mt-2')
        # ДОДАЛИ ВАРІАНТ "РАЗОВО"
        schedule_type = ui.toggle(
            {'hourly': 'Щогодини', 'daily': 'Щодня', 'weekly': 'По днях', 'once': 'Разово'},
            value='daily'
        ).classes('w-full mb-4 justify-center')

        # --- Блоки часу ---
        with ui.column().classes('w-full gap-2') as hourly_container:
            hourly_min = ui.number('На якій хвилині бити? (0-59)', value=0, min=0, max=59, format='%.0f').classes(
                'w-full')

        with ui.column().classes('w-full gap-2') as daily_container:
            daily_time = ui.input('Час (ГГ:ХХ)', value='12:00').classes('w-full')
            with ui.menu().classes('p-0') as daily_time_menu:
                ui.time().bind_value(daily_time)
            with daily_time.add_slot('append'):
                ui.icon('access_time').classes('cursor-pointer text-blue-600').on('click', daily_time_menu.open)

        with ui.column().classes('w-full gap-2') as weekly_container:
            weekly_time = ui.input('Час (ГГ:ХХ)', value='08:30').classes('w-full')
            with ui.menu().classes('p-0') as weekly_time_menu:
                ui.time().bind_value(weekly_time)
            with weekly_time.add_slot('append'):
                ui.icon('access_time').classes('cursor-pointer text-blue-600').on('click', weekly_time_menu.open)

            days_options = {'1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт', '5': 'Пт', '6': 'Сб', '0': 'Нд'}
            weekly_days = ui.select(options=days_options, multiple=True, label='Дні тижня',
                                    value=['1', '2', '3', '4', '5']).classes('w-full')

        # НОВИЙ БЛОК: РАЗОВА ПОДІЯ (з Календарем)
        with ui.column().classes('w-full gap-2') as once_container:
            once_date = ui.input('Дата (РРРР-ММ-ДД)', value='2026-09-01').classes('w-full')
            with ui.menu().classes('p-0') as once_date_menu:
                ui.date(mask='YYYY-MM-DD').bind_value(once_date)
            with once_date.add_slot('append'):
                ui.icon('calendar_today').classes('cursor-pointer text-blue-600').on('click', once_date_menu.open)

            once_time = ui.input('Час (ГГ:ХХ)', value='08:30').classes('w-full')
            with ui.menu().classes('p-0') as once_time_menu:
                ui.time().bind_value(once_time)
            with once_time.add_slot('append'):
                ui.icon('access_time').classes('cursor-pointer text-blue-600').on('click', once_time_menu.open)

        def update_visibility():
            hourly_container.set_visibility(schedule_type.value == 'hourly')
            daily_container.set_visibility(schedule_type.value == 'daily')
            weekly_container.set_visibility(schedule_type.value == 'weekly')
            once_container.set_visibility(schedule_type.value == 'once')

        schedule_type.on_value_change(update_visibility)
        update_visibility()

        media_input = ui.select(options=[], label='Аудіофайл').classes('w-full mt-4')

        def save_event():
            if not name_input.value or not media_input.value or media_input.value == "Файли не знайдені":
                ui.notify('Заповніть назву і оберіть файл!', type='negative')
                return

            try:
                if schedule_type.value == 'hourly':
                    cron_expr = f"{int(hourly_min.value)} * * * *"
                elif schedule_type.value == 'daily':
                    h, m = daily_time.value.split(':')
                    cron_expr = f"{int(m)} {int(h)} * * *"
                elif schedule_type.value == 'weekly':
                    h, m = weekly_time.value.split(':')
                    if not weekly_days.value:
                        ui.notify('Оберіть дні!', type='warning')
                        return
                    cron_expr = f"{int(m)} {int(h)} * * {','.join(weekly_days.value)}"
                elif schedule_type.value == 'once':
                    # ЗБЕРІГАЄМО ЯК ДАТУ ЗІ СПЕЦІАЛЬНИМ ПРЕФІКСОМ
                    if not once_date.value or not once_time.value:
                        ui.notify('Заповніть дату та час!', type='warning')
                        return
                    cron_expr = f"DATE:{once_date.value} {once_time.value}"

            except Exception:
                ui.notify('Помилка формату часу!', type='negative')
                return

            if current_edit_id["id"] is None:
                add_audio_event(name_input.value, cron_expr, media_input.value)
                ui.notify('Подію успішно створено!', type='positive')
            else:
                update_audio_event(current_edit_id["id"], name_input.value, cron_expr, media_input.value)
                ui.notify('Подію успішно оновлено!', type='positive')

            dialog.close()
            events_table.refresh()
            reload_jobs()

        with ui.row().classes('w-full justify-end mt-6 gap-2'):
            ui.button('Скасувати', on_click=dialog.close, color='gray')
            ui.button('Зберегти', on_click=save_event, color='primary')

    def open_create_dialog():
        current_edit_id["id"] = None
        dialog_title.set_text('Додати нову подію')
        name_input.value = ''
        media_input.options = get_media_files()
        media_input.value = None
        media_input.update()
        dialog.open()

    def open_edit_dialog(row_data):
        current_edit_id["id"] = row_data['id']
        dialog_title.set_text('Редагувати подію')
        name_input.value = row_data['name']

        media_input.options = get_media_files()
        media_input.value = row_data['media_file']
        media_input.update()

        expr = row_data['cron_expression']

        # РОЗШИФРОВКА DATE ТА CRON
        if expr.startswith('DATE:'):
            schedule_type.value = 'once'
            date_str, time_str = expr.replace('DATE:', '').split(' ')
            once_date.value = date_str
            once_time.value = time_str
        else:
            parts = expr.split()
            if len(parts) == 5:
                if parts[1] == '*' and parts[2] == '*' and parts[3] == '*' and parts[4] == '*':
                    schedule_type.value = 'hourly'
                    hourly_min.value = int(parts[0])
                elif parts[2] == '*' and parts[3] == '*' and parts[4] == '*':
                    schedule_type.value = 'daily'
                    daily_time.value = f"{int(parts[1]):02d}:{int(parts[0]):02d}"
                elif parts[2] == '*' and parts[3] == '*':
                    schedule_type.value = 'weekly'
                    weekly_time.value = f"{int(parts[1]):02d}:{int(parts[0]):02d}"
                    weekly_days.value = parts[4].split(',')

        dialog.open()

    with ui.row().classes('w-full justify-between items-center mb-4'):
        ui.label('Список запланованих подій').classes('text-subtitle1 text-gray-600')
        with ui.row().classes('gap-4'):
            ui.button('Завантажити аудіо', on_click=upload_dialog.open, icon='upload_file').classes('bg-blue-600')
            ui.button('Додати подію', on_click=open_create_dialog, icon='add').classes('bg-green-600')

    @ui.refreshable
    def events_table():
        events = get_all_events()

        if not events:
            with ui.card().classes('w-full items-center py-8 bg-gray-50'):
                ui.icon('event_busy', size='4rem', color='gray-400')
                ui.label('Розклад порожній.').classes('text-gray-500 mt-2')
            return

        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
            {'name': 'name', 'label': 'Назва події', 'field': 'name', 'align': 'left'},
            {'name': 'cron', 'label': 'Розклад', 'field': 'cron_expression', 'align': 'left'},
            {'name': 'media', 'label': 'Медіафайл', 'field': 'media_file', 'align': 'left'},
            {'name': 'status', 'label': 'Статус', 'field': 'is_active', 'align': 'center'},
            {'name': 'actions', 'label': 'Керування', 'field': 'actions', 'align': 'center'},
        ]

        rows = [{
            'id': e.id, 'name': e.name,
            'cron_expression': e.cron_expression.replace('DATE:', '📅 ') if e.cron_expression.startswith(
                'DATE:') else f"⏱️ {e.cron_expression}",
            'media_file': e.media_file, 'is_active': '✅ Активно' if e.is_active else '⏸️ Пауза',
            'is_active_raw': e.is_active
        } for e in events]

        table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full shadow-sm')

        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round size="sm" :icon="props.row.is_active_raw ? 'pause' : 'play_arrow'" :color="props.row.is_active_raw ? 'warning' : 'positive'" @click="() => $parent.$emit('toggle', props.row)" />
                <q-btn flat round size="sm" icon="edit" color="info" @click="() => $parent.$emit('edit', props.row)" />
                <q-btn flat round size="sm" icon="delete" color="negative" @click="() => $parent.$emit('delete', props.row)" />
            </q-td>
        ''')

        table.on('toggle', lambda e: [toggle_audio_event(e.args['id']), events_table.refresh(), reload_jobs()])
        table.on('edit', lambda e: open_edit_dialog(e.args))
        table.on('delete', lambda e: [delete_audio_event(e.args['id']), events_table.refresh(), reload_jobs()])

    events_table()