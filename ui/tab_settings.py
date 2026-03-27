import subprocess
import sys
from pathlib import Path
from nicegui import ui, app
from database.crud import get_system_settings, engine, update_user_password
from sqlmodel import Session
from core.system_control import reboot_pi, update_wifi_settings

def save_settings(settings_obj):
    with Session(engine) as session:
        session.merge(settings_obj)
        session.commit()
    ui.notify('Налаштування збережено!', type='positive')


def build_settings_tab():
    ui.label('Глобальні налаштування системи').classes('text-h6 mb-4')
    settings = get_system_settings()
    if not settings:
        ui.label('Помилка завантаження налаштувань.').classes('text-red-500')
        return

    with ui.card().classes('w-full max-w-4xl p-6'):
        # ==========================================
        # 1. ЛОГІКА СИСТЕМНИХ ЗВУКІВ
        # ==========================================
        ui.label('Логіка системних звуків').classes('text-subtitle1 font-bold mb-2')
        ui.label('Коли грати переддзвін (мелодію перед ударами):').classes('w-1/2 font-medium text-gray-700')
        with ui.row().classes('w-full items-center mb-2'):
            ui.select(
                options={'12_24': 'Тільки о 12:00 та 00:00', 'hourly': 'Щогодини', 'none': 'Вимкнути взагалі'},
                value='12_24'
            ).bind_value(settings, 'pre_chime_mode').classes('flex-1')
            ui.button('Зберегти', on_click=lambda: save_settings(settings), icon='save').classes(
            'flex-1 bg-primary shadow-md text-white')
        # ==========================================
        # 2. ЗАВАНТАЖЕННЯ СИСТЕМНИХ ЗВУКІВ (НОВИЙ БЛОК)
        # ==========================================
        ui.label('Заміна системних файлів').classes('text-subtitle2 font-bold mt-6 mb-1 text-gray-800')
        ui.label(
            'Завантажте ваші аудіофайли сюди. Програма автоматично перейменує їх для правильної роботи Оркестратора.').classes(
            'text-sm text-gray-500 mb-4')

        with ui.row().classes('w-full justify-between gap-4 mb-6'):
            def create_sys_uploader(title, target_filename, icon_name):
                with ui.column().classes('items-center border p-4 rounded-lg flex-1 bg-gray-50'):
                    ui.icon(icon_name, size='2rem', color='gray-400')
                    ui.label(title).classes('font-medium text-center mt-2')
                    ui.label(target_filename).classes('text-xs text-secondary font-mono mb-2')

                    async def handle(e, name=target_filename, t=title):
                        media_dir = Path("storage/media")
                        media_dir.mkdir(parents=True, exist_ok=True)

                        # Тут ми ЖОРСТКО ПЕРЕЗАПИСУЄМО файл під потрібним іменем
                        file_bytes = await e.file.read()
                        with open(media_dir / name, 'wb') as f:
                            f.write(file_bytes)

                        ui.notify(f'{t} успішно оновлено!', type='positive')
                        # Очищаємо компонент після завантаження
                        #e.sender.reset()

                    ui.upload(on_upload=handle, auto_upload=True, multiple=False, label="Завантажити").classes(
                        'w-full').props('accept=".mp3,.wav,.ogg"')

            # Створюємо 3 спеціальні завантажувачі
            create_sys_uploader('Переддзвін (Довга мелодія)', 'melody.mp3', 'music_note')
            create_sys_uploader('Бій курантів (1 удар)', 'knock.mp3', 'notifications_active')
            create_sys_uploader('Вокзальний гонг (Увага)', 'attention.mp3', 'campaign')

        ui.separator().classes('mb-6')

        # ==========================================
        # 3. НАЛАШТУВАННЯ МЕХАНІКИ
        # ==========================================
        ui.label('Налаштування механіки (Шестерні)').classes('text-subtitle1 font-bold mb-2')
        with ui.row().classes('w-full items-center mb-6'):
            ui.label('Кроків на 1 хвилину:').classes('w-1/3 font-medium text-gray-700')
            ui.number(value=125).bind_value(settings, 'steps_per_minute_dial').classes('w-1/4')

        with ui.row().classes('w-full items-center mb-6'):
            ui.label('Звичайний крок триває:').classes('w-1/3 font-medium text-gray-700')
            ui.slider(min=0.5, max=10.0, step=0.5).bind_value(settings, 'normal_move_sec').classes('w-1/3')
            ui.number(suffix=' сек').bind_value(settings, 'normal_move_sec').classes('w-1/5 ml-4')

        with ui.row().classes('w-full items-center mb-8'):
            ui.label('Крок калібрування триває:').classes('w-1/3 font-medium text-gray-700')
            ui.slider(min=0.05, max=2.0, step=0.05).bind_value(settings, 'fast_move_sec').classes(
                'w-1/3 text-accent')
            ui.number(suffix=' сек').bind_value(settings, 'fast_move_sec').classes('w-1/5 ml-4')
        ui.button('Зберегти параметри', on_click=lambda: save_settings(settings), icon='save').classes(
            'w-full bg-primary shadow-md text-white')
        # ==========================================
        # БЛОК OTA-ОНОВЛЕНЬ (GITHUB)
        # ==========================================
        ui.separator().classes('my-6')
        ui.label('Оновлення системи (GitHub)').classes('text-subtitle1 font-bold mb-2')

        with ui.card().classes('w-full p-4 border border-gray-200 bg-gray-50'):
            update_status = ui.label('Стан: Готово до перевірки').classes('text-gray-600 mb-4 font-medium')

            with ui.row().classes('gap-4 items-center'):
                def check_update():
                    update_status.set_text('Стан: Зв\'язок з GitHub...')
                    try:
                        # Завантажуємо інформацію про гілку з сервера
                        subprocess.run(['git', 'fetch'], check=True, capture_output=True)

                        # Рахуємо, на скільки комітів наша локальна версія ВІДСТАЄ від сервера
                        behind_count_str = subprocess.check_output(
                            ['git', 'rev-list', 'HEAD..@{u}', '--count']
                        ).decode('utf-8').strip()

                        commits_behind = int(behind_count_str)

                        if commits_behind == 0:
                            update_status.set_text('Стан: У вас встановлена остання версія ✅')
                            update_status.classes(replace='text-positive mb-4 font-bold')
                            btn_apply_update.set_visibility(False)
                        else:
                            update_status.set_text(f'Стан: Доступне оновлення ({commits_behind} нових комітів) 🚀')
                            update_status.classes(replace='text-accent mb-4 font-bold')
                            btn_apply_update.set_visibility(True)
                    except Exception as e:
                        update_status.set_text(f'Помилка перевірки (перевірте інтернет): {e}')
                        update_status.classes(replace='text-negative mb-4 font-bold')

                def apply_update():
                    ui.notify('Оновлення коду та залежностей... Система перезапуститься.', type='warning',
                              timeout=10000)
                    try:
                        # 1. Примусово синхронізуємо локальні файли з гітхабом
                        subprocess.run(['git', 'reset', '--hard'], check=True)
                        subprocess.run(['git', 'pull'], check=True)

                        # 2. Оновлюємо залежності (якщо з'явилися нові бібліотеки)
                        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
                        # 3. Перезапускаємо саму службу (вб'є поточний процес і запустить новий)
                        subprocess.Popen(['systemctl', 'restart', 'towerclock.service'])
                    except Exception as e:
                        ui.notify(f'Помилка оновлення: {e}', type='negative')

                ui.button('Перевірити оновлення', icon='sync', on_click=check_update).classes('bg-secondary text-white')

                # Кнопка встановлення (спочатку прихована)
                btn_apply_update = ui.button('Встановити та Перезапустити', icon='download',
                                             on_click=apply_update).classes('bg-primary text-white')
                btn_apply_update.set_visibility(False)        # ==========================================
        # МЕРЕЖА І СИСТЕМА
        # ==========================================
        ui.separator().classes('my-6')
        ui.label('Безпека').classes('text-subtitle1 font-bold mb-2')
        with ui.row().classes('w-full items-center gap-4 mb-4'):
            new_pass = ui.input('Новий пароль адміністратора', password=True, password_toggle_button=True).classes(
                'flex-1')

            def change_pass():
                if len(new_pass.value) < 4:
                    ui.notify('Пароль занадто короткий!', type='negative')
                    return
                # Беремо ім'я поточного користувача з сесії app.storage.user
                username = app.storage.user.get('username', 'admin')
                if update_user_password(username, new_pass.value):
                    ui.notify('Пароль успішно змінено!', type='positive')
                    new_pass.value = ''
                else:
                    ui.notify('Помилка бази даних', type='negative')

            ui.button('Оновити пароль', on_click=change_pass, icon='lock_reset').classes('bg-accent')

        ui.separator().classes('my-6')
        ui.label('Мережа та Система').classes('text-subtitle1 font-bold mb-2')

        with ui.card().classes('w-full p-4 border border-secondary bg-gray-100'):
            ui.label('Налаштування Wi-Fi Точки доступу').classes('font-bold text-primary mb-4')

            with ui.row().classes('w-full gap-4 items-center'):
                wifi_ssid = ui.input('Назва (SSID)', value='TowerClock').classes('flex-1 bg-white px-2 rounded')
                wifi_pass = ui.input('Пароль Wi-Fi', value='This is tower clock of KPI').classes('flex-1 bg-white px-2 rounded')

                async def apply_wifi():
                    if len(wifi_pass.value) < 8:
                        ui.notify('Пароль має бути мін. 8 символів!', type='negative')
                        return

                    # Попереджаємо, що з'єднання розірветься
                    with ui.dialog() as diag, ui.card():
                        ui.label(
                            'Увага! Після зміни налаштувань Wi-Fi ваш пристрій від’єднається. Бажаєте продовжити?').classes(
                            'mb-4')
                        with ui.row():
                            ui.button('ТАК', on_click=lambda: diag.submit(True), color='primary')
                            ui.button('Скасувати', on_click=lambda: diag.submit(False), color='gray')

                    if await diag:
                        ui.notify('Застосування... Перепідключіться до нової мережі через хвилину.', type='warning')
                        update_wifi_settings(wifi_ssid.value, wifi_pass.value)

                ui.button('Застосувати', icon='wifi', on_click=apply_wifi).classes('bg-secondary text-white')

        # Блок перезавантаження (виносимо окремо, щоб випадково не натиснути)
        with ui.row().classes('w-full justify-end mt-8'):
            async def confirm_reboot():
                with ui.dialog() as diag, ui.card():
                    ui.label('Ви впевнені, що хочете ПЕРЕЗАВАНТАЖИТИ контролер?').classes('text-h6 mb-4')
                    ui.label('Система буде недоступна приблизно 1-2 хвилини.').classes('mb-4 text-gray-500')
                    with ui.row().classes('w-full justify-end gap-4'):
                        ui.button('СКАСУВАТИ', on_click=lambda: diag.submit(False), color='gray')
                        ui.button('ПЕРЕЗАВАНТАЖИТИ', on_click=lambda: diag.submit(True), color='red')

                if await diag:
                    ui.notify('Команда відправлена. До зустрічі через хвилину!', type='negative')
                    reboot_pi()

            ui.button('Перезавантажити Orange Pi', icon='restart_alt', on_click=confirm_reboot).classes(
                'bg-negative text-white shadow-lg')