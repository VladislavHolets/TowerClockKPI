from pathlib import Path
from datetime import datetime
from nicegui import ui
from database.crud import get_all_events, add_audio_event, toggle_audio_event, delete_audio_event, update_audio_event
from core.scheduler import reload_jobs

current_edit_id = {"id": None}


def get_media_files():
    """Повертає список існуючих аудіофайлів (або порожній список)"""
    media_dir = Path("storage/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    valid_extensions = {'.mp3', '.wav', '.ogg'}
    return [f.name for f in media_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]


def build_schedule_tab():
    ui.label('Керування розкладом аудіо подій').classes('text-h6 mb-4')

    # ==========================================
    # 1. ЗАВАНТАЖЕННЯ МЕДІА (з постфіксами)
    # ==========================================
    with ui.dialog() as upload_dialog, ui.card().classes('min-w-[400px]'):
        ui.label('Завантажити новий аудіофайл').classes('text-h6 font-bold')
        ui.label('Підтримуються формати: .mp3, .wav, .ogg').classes('text-caption text-gray-500 mb-2')

        async def handle_upload(e):
            media_dir = Path("storage/media")
            original_name = e.file.name
            file_path = media_dir / original_name

            # ЗАХИСТ ВІД ПЕРЕЗАПИСУ: додаємо _1, _2 якщо файл існує
            counter = 1
            while file_path.exists():
                stem = Path(original_name).stem
                suffix = Path(original_name).suffix
                new_name = f"{stem}_{counter}{suffix}"
                file_path = media_dir / new_name
                counter += 1

            file_bytes = await e.file.read()
            with open(file_path, 'wb') as f:
                f.write(file_bytes)

            ui.notify(f'Файл збережено як "{file_path.name}"!', type='positive')

            # Оновлюємо списки
            media_input.options = get_media_files() or ["Файли не знайдені"]
            media_input.update()
            manage_media_list.refresh()

            upload_dialog.close()

        ui.upload(on_upload=handle_upload, multiple=False, auto_upload=True, label="Перетягніть файл сюди").classes(
            'w-full')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Закрити', on_click=upload_dialog.close, color='gray')

    # ==========================================
    # 2. КЕРУВАННЯ ТА ВИДАЛЕННЯ ФАЙЛІВ
    # ==========================================
    with ui.dialog() as manage_media_dialog, ui.card().classes('min-w-[400px]'):
        ui.label('Керування аудіофайлами').classes('text-h6 font-bold mb-4')

        @ui.refreshable
        def manage_media_list():
            files = get_media_files()
            if not files:
                ui.label('Немає завантажених файлів.').classes('text-gray-500 italic')
                return

            for filename in files:
                with ui.row().classes('w-full justify-between items-center border-b pb-2 mb-2'):
                    ui.label(filename).classes('truncate max-w-[250px]')
                    ui.button(icon='delete', color='negative', on_click=lambda f=filename: delete_media_file(f)).props(
                        'flat round size=sm').tooltip('Видалити файл')

        def delete_media_file(filename):
            file_path = Path("storage/media") / filename
            if file_path.exists():
                file_path.unlink()  # Фізичне видалення файлу
                ui.notify(f'Файл "{filename}" видалено', type='info')

                # Оновлюємо UI
                manage_media_list.refresh()
                media_input.options = get_media_files() or ["Файли не знайдені"]
                if media_input.value == filename:
                    media_input.value = None
                media_input.update()

        manage_media_list()

        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Закрити', on_click=manage_media_dialog.close, color='gray')

    # ==========================================
    # 3. ВІКНО ДОДАВАННЯ ПОДІЇ
    # ==========================================
    with ui.dialog() as dialog, ui.card().classes('min-w-[450px]'):
        dialog_title = ui.label('Додати нову подію').classes('text-h6 font-bold')
        name_input = ui.input('Назва (напр. Екскурсія)').classes('w-full mb-2')

        ui.label('Як часто відтворювати?').classes('text-sm text-gray-600 mt-2')
        schedule_type = ui.toggle(
            {'hourly': 'Щогодини', 'daily': 'Щодня', 'weekly': 'По днях', 'once': 'Разово'},
            value='daily'
        ).classes('w-full mb-4 justify-center')

        with ui.column().classes('w-full gap-2') as hourly_container:
            hourly_min = ui.number('На якій хвилині бити? (0-59)', value=0, min=0, max=59, format='%.0f').classes(
                'w-full')

        # --- ТУТ МИ ВИПРАВИЛИ ПОЗИЦІЮВАННЯ ВІДЖЕТІВ ---
        with ui.column().classes('w-full gap-2') as daily_container:
            with ui.element('div').classes('w-full'):
                daily_time = ui.input('Час (ГГ:ХХ)', value='12:00').classes('w-full')
                with ui.menu().classes('p-0').props('anchor="bottom left" self="top left"') as daily_time_menu:
                    ui.time().bind_value(daily_time)
                with daily_time.add_slot('append'):
                    ui.icon('access_time').classes('cursor-pointer text-primary').on('click', daily_time_menu.open)

        with ui.column().classes('w-full gap-2') as weekly_container:
            with ui.element('div').classes('w-full'):
                weekly_time = ui.input('Час (ГГ:ХХ)', value='08:30').classes('w-full')
                with ui.menu().classes('p-0').props('anchor="bottom left" self="top left"') as weekly_time_menu:
                    ui.time().bind_value(weekly_time)
                with weekly_time.add_slot('append'):
                    ui.icon('access_time').classes('cursor-pointer text-primary').on('click', weekly_time_menu.open)

            days_options = {'1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт', '5': 'Пт', '6': 'Сб', '0': 'Нд'}
            weekly_days = ui.select(options=days_options, multiple=True, label='Дні тижня',
                                    value=['1', '2', '3', '4', '5']).classes('w-full')

        with ui.column().classes('w-full gap-2') as once_container:
            # 1. Блок ДАТИ
            with ui.element('div').classes('w-full'):
                once_date = ui.input('Дата (РРРР-ММ-ДД)', value='').classes('w-full')
                with ui.menu().classes('p-0').props('anchor="bottom left" self="top left"') as once_date_menu:
                    ui.date(mask='YYYY-MM-DD').bind_value(once_date)
                with once_date.add_slot('append'):
                    ui.icon('calendar_today').classes('cursor-pointer text-primary').on('click', once_date_menu.open)

            # 2. Блок ЧАСУ
            with ui.element('div').classes('w-full'):
                once_time = ui.input('Час (ГГ:ХХ)', value='').classes('w-full')
                with ui.menu().classes('p-0').props('anchor="bottom left" self="top left"') as once_time_menu:
                    ui.time().bind_value(once_time)
                with once_time.add_slot('append'):
                    ui.icon('access_time').classes('cursor-pointer text-primary').on('click', once_time_menu.open)

        def update_visibility():
            hourly_container.set_visibility(schedule_type.value == 'hourly')
            daily_container.set_visibility(schedule_type.value == 'daily')
            weekly_container.set_visibility(schedule_type.value == 'weekly')
            once_container.set_visibility(schedule_type.value == 'once')

        schedule_type.on_value_change(update_visibility)
        update_visibility()

        # Вибір аудіо
        media_input = ui.select(options=[], label='Аудіофайл').classes('w-full mt-4')
        play_attention_toggle = ui.checkbox('Грати звук сповіщення ("вокзальний" гонг) перед подією',
                                            value=False).classes('mt-2 text-gray-700')

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
                    if not once_date.value or not once_time.value:
                        ui.notify('Заповніть дату та час!', type='warning')
                        return
                    cron_expr = f"DATE:{once_date.value} {once_time.value}"
            except Exception:
                ui.notify('Помилка формату часу!', type='negative')
                return

            if current_edit_id["id"] is None:
                add_audio_event(name_input.value, cron_expr, media_input.value, play_attention_toggle.value)
                ui.notify('Подію успішно створено!', type='positive')
            else:
                update_audio_event(current_edit_id["id"], name_input.value, cron_expr, media_input.value,
                                   play_attention_toggle.value)
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
        media_input.options = get_media_files() or ["Файли не знайдені"]
        media_input.value = None
        media_input.update()
        play_attention_toggle.value = False

        # ДИНАМІЧНИЙ ПОТОЧНИЙ ЧАС ДЛЯ РАЗОВОЇ ПОДІЇ
        now = datetime.now()
        once_date.value = now.strftime('%Y-%m-%d')
        once_time.value = now.strftime('%H:%M')

        dialog.open()

    def open_edit_dialog(row_data):
        current_edit_id["id"] = row_data['id']
        dialog_title.set_text('Редагувати подію')
        name_input.value = row_data['name']
        media_input.options = get_media_files() or ["Файли не знайдені"]
        media_input.value = row_data['media_file']
        media_input.update()

        play_attention_toggle.value = row_data.get('play_attention', False)

        expr = row_data['cron_expression']
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

    # ==========================================
    # 4. ВЕРХНЯ ПАНЕЛЬ КЕРУВАННЯ
    # ==========================================
    with ui.row().classes('w-full justify-between items-center mb-4'):
        ui.label('Список запланованих подій').classes('text-subtitle1 text-gray-600')
        with ui.row().classes('gap-4'):
            # Додали кнопку Керування файлами
            ui.button('Файли', on_click=manage_media_dialog.open, icon='folder').classes('bg-secondary')
            ui.button('Завантажити аудіо', on_click=upload_dialog.open, icon='upload_file').classes('bg-primary')
            ui.button('Додати подію', on_click=open_create_dialog, icon='add').classes('bg-accent text-white font-bold')

    # ==========================================
    # 5. ТАБЛИЦЯ ПОДІЙ
    # ==========================================
    @ui.refreshable
    def events_table():
        events = get_all_events()
        if not events:
            with ui.card().classes('w-full items-center py-8 bg-gray-50'):
                ui.icon('event_busy', size='4rem', color='gray-400')
                ui.label('Розклад порожній.').classes('text-gray-500 mt-2')
            return

        columns = [
            {'name': 'name', 'label': 'Назва події', 'field': 'name', 'align': 'left'},
            # ЗВЕРНІТЬ УВАГУ: Тепер колонка дивиться на поле cron_display
            {'name': 'cron', 'label': 'Розклад', 'field': 'cron_display', 'align': 'left'},
            {'name': 'media', 'label': 'Медіафайл', 'field': 'media_file', 'align': 'left'},
            {'name': 'attention', 'label': 'Гонг', 'field': 'attention_icon', 'align': 'center'},
            {'name': 'status', 'label': 'Статус', 'field': 'is_active', 'align': 'center'},
            {'name': 'actions', 'label': 'Керування', 'field': 'actions', 'align': 'center'},
        ]

        rows = [{
            'id': e.id,
            'name': e.name,
            # ЗАЛИШАЄМО чистий код для функції редагування
            'cron_expression': e.cron_expression,
            # ДОДАЄМО нове поле з емодзі суто для краси в таблиці
            'cron_display': e.cron_expression.replace('DATE:', '📅 ') if e.cron_expression.startswith(
                'DATE:') else f"⏱️ {e.cron_expression}",
            'media_file': e.media_file,
            'attention_icon': '🔔' if e.play_attention else '—',
            'play_attention': e.play_attention,
            'is_active': '✅ Активно' if e.is_active else '⏸️ Пауза',
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