import json  # [НОВЕ] Додано для роботи з JSON-форматом тихих годин
import subprocess
import sys
from pathlib import Path
from nicegui import ui, app
from database.crud import get_system_settings, engine, update_user_password
from sqlmodel import Session
from core.system_control import reboot_pi, update_wifi_settings
from hardware.audio import play_test_file


# [ОНОВЛЕНО] Тепер функція приймає список тихих годин, щоб запакувати його перед збереженням
def save_settings(settings_obj, qh_list):
    settings_obj.quiet_hours = json.dumps(qh_list)
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

    # [НОВЕ] Розпаковуємо тихі години з БД або створюємо стандартний період
    try:
        qh_list = json.loads(settings.quiet_hours)
    except:
        qh_list = [{"start": "22:00", "end": "08:00"}]

    with ui.card().classes('w-full max-w-4xl p-6'):

        # ==========================================
        # 0. ТИХІ ГОДИНИ (НОВИЙ БЛОК)
        # ==========================================
        ui.label('Періоди тиші').classes('text-subtitle1 font-bold mb-2')
        ui.label('У цей час годинник не відтворюватиме жодних звуків (ні курантів, ні розкладу).').classes(
            'text-sm text-gray-500 mb-4')

        qh_container = ui.column().classes('w-full gap-2 mb-4')

        def render_qh():
            qh_container.clear()
            with qh_container:
                if not qh_list:
                    ui.label('Немає активних періодів тиші.').classes('text-gray-500 italic text-sm')

                for i, qh in enumerate(qh_list):
                    with ui.row().classes('w-full items-center gap-4 bg-gray-100 p-2 rounded border border-gray-300'):
                        ui.label(f'Період {i + 1}:').classes('font-medium text-primary text-sm w-20')

                        # === Віджет "ВІД" ===
                        with ui.input('Від (ГГ:ХХ)', value=qh.get('start', '22:00')).classes(
                                'w-32 bg-white px-2 rounded') as start_inp:
                            # Додаємо меню з віджетом годинника
                            with ui.menu().classes('p-0').props('anchor="bottom left" self="top left"') as start_menu:
                                ui.time().bind_value(start_inp)
                            # Іконка для відкриття меню
                            with start_inp.add_slot('append'):
                                ui.icon('access_time').classes('cursor-pointer text-primary').on('click',
                                                                                                 start_menu.open)
                            # Зберігаємо значення при зміні
                            start_inp.on_value_change(lambda e, idx=i: qh_list[idx].update({'start': e.value}))

                        # === Віджет "ДО" ===
                        with ui.input('До (ГГ:ХХ)', value=qh.get('end', '08:00')).classes(
                                'w-32 bg-white px-2 rounded') as end_inp:
                            with ui.menu().classes('p-0').props('anchor="bottom left" self="top left"') as end_menu:
                                ui.time().bind_value(end_inp)
                            with end_inp.add_slot('append'):
                                ui.icon('access_time').classes('cursor-pointer text-primary').on('click', end_menu.open)
                            end_inp.on_value_change(lambda e, idx=i: qh_list[idx].update({'end': e.value}))

                        ui.space()
                        ui.button(icon='delete', color='negative',
                                  on_click=lambda idx=i: [qh_list.pop(idx), render_qh()]).props(
                            'flat round size=sm').tooltip('Видалити період')
        render_qh()
        ui.button('Додати період тиші', icon='add',
                  on_click=lambda: [qh_list.append({"start": "00:00", "end": "06:00"}), render_qh()]).classes(
            'bg-secondary text-white mb-6')

        ui.separator().classes('mb-6')

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
            # [ОНОВЛЕНО] Передаємо qh_list у кнопку збереження
            ui.button('Зберегти', on_click=lambda: save_settings(settings, qh_list), icon='save').classes(
                'flex-1 bg-primary shadow-md text-white')

        # ==========================================
        # 2. ЗАВАНТАЖЕННЯ СИСТЕМНИХ ЗВУКІВ ТА ГУЧНІСТЬ
        # ==========================================
        ui.label('Заміна системних файлів').classes('text-subtitle2 font-bold mt-6 mb-1 text-gray-800')
        ui.label(
            'Завантажте ваші аудіофайли сюди. Програма автоматично перейменує їх для правильної роботи Оркестратора.').classes(
            'text-sm text-gray-500 mb-4')

        with ui.row().classes('w-full justify-between gap-4 mb-6'):
            # [ОНОВЛЕНО] Додано параметр vol_field для прив'язки потрібної гучності
            def create_sys_uploader(title, target_filename, icon_name, vol_field):
                with ui.column().classes('items-center border p-4 rounded-lg flex-1 bg-gray-50'):
                    ui.icon(icon_name, size='2rem', color='gray-400')
                    ui.label(title).classes('font-medium text-center mt-2')
                    ui.label(target_filename).classes('text-xs text-secondary font-mono mb-2')

                    # [НОВЕ] Слайдер гучності
                    with ui.row().classes('w-full items-center gap-2 mb-4'):
                        ui.icon('volume_down', size='sm').classes('text-gray-500')
                        ui.slider(min=0, max=100).bind_value(settings, vol_field).classes('flex-1 text-accent').on(
                            'change', lambda: save_settings(settings, qh_list)
                        )
                        ui.label().bind_text_from(settings, vol_field, backward=lambda v: f"{v}%").classes(
                            'text-xs text-gray-600 font-mono w-8 text-right')

                    # [НОВЕ] Функція та блок кнопок (Тест + Завантаження)
                    def test_sound(filename, vol):
                        filepath = Path("storage/media") / filename
                        if filepath.exists():
                            ui.notify(f'Тестування {filename} ({vol}%)', type='info')
                            play_test_file(filename, vol)
                        else:
                            ui.notify(f'Файл {filename} відсутній!', type='warning')

                    with ui.row().classes('w-full items-center gap-2'):
                        ui.button(icon='play_arrow', on_click=lambda f=target_filename, v=vol_field: test_sound(f,
                                                                                                                getattr(
                                                                                                                    settings,
                                                                                                                    v))).classes(
                            'bg-info text-white').props('dense padding="sm"').tooltip('Протестувати')

                        async def handle(e, name=target_filename, t=title):
                            media_dir = Path("storage/media")
                            media_dir.mkdir(parents=True, exist_ok=True)
                            file_bytes = await e.file.read()
                            with open(media_dir / name, 'wb') as f:
                                f.write(file_bytes)
                            ui.notify(f'{t} успішно оновлено!', type='positive')

                        ui.upload(on_upload=handle, auto_upload=True, multiple=False, label="Завантажити").classes(
                            'flex-1').props('accept=".mp3,.wav,.ogg"')

            # [ОНОВЛЕНО] Викликаємо з прив'язкою до полів бази даних
            create_sys_uploader('Переддзвін (Довга мелодія)', 'melody.mp3', 'music_note', 'vol_melody')
            create_sys_uploader('Бій курантів (1 удар)', 'knock.mp3', 'notifications_active', 'vol_knock')
            create_sys_uploader('Вокзальний гонг (Увага)', 'attention.mp3', 'campaign', 'vol_attention')

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

        # [ОНОВЛЕНО] Передаємо qh_list у кнопку збереження
        ui.button('Зберегти параметри', on_click=lambda: save_settings(settings, qh_list), icon='save').classes(
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
                        subprocess.run(['git', 'fetch'], check=True, capture_output=True)
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
                        subprocess.run(['git', 'reset', '--hard'], check=True)
                        subprocess.run(['git', 'pull'], check=True)
                        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
                        subprocess.Popen(['systemctl', 'restart', 'towerclock.service'])
                    except Exception as e:
                        ui.notify(f'Помилка оновлення: {e}', type='negative')

                ui.button('Перевірити оновлення', icon='sync', on_click=check_update).classes('bg-secondary text-white')

                btn_apply_update = ui.button('Встановити та Перезапустити', icon='download',
                                             on_click=apply_update).classes('bg-primary text-white')
                btn_apply_update.set_visibility(False)

                # ==========================================
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
                wifi_pass = ui.input('Пароль Wi-Fi', value='This is tower clock of KPI').classes(
                    'flex-1 bg-white px-2 rounded')

                async def apply_wifi():
                    if len(wifi_pass.value) < 8:
                        ui.notify('Пароль має бути мін. 8 символів!', type='negative')
                        return

                    with ui.dialog() as diag, ui.card():
                        ui.label(
                            'Увага! Після зміни налаштувань Wi-Fi ваш пристрій від’єднається. Бажаєте продовжити?').classes(
                            'mb-4')
                        with ui.row():
                            ui.button('ТАК', on_click=lambda: diag.submit(True), color='primary')
                            ui.button('Скасувати', on_click=lambda: diag.submit(False), color='red')

                    if await diag:
                        ui.notify('Застосування... Перепідключіться до нової мережі через хвилину.', type='warning')
                        update_wifi_settings(wifi_ssid.value, wifi_pass.value)

                ui.button('Застосувати', icon='wifi', on_click=apply_wifi).classes('bg-secondary text-white')

        with ui.row().classes('w-full justify-end mt-8'):
            async def confirm_reboot():
                with ui.dialog() as diag, ui.card():
                    ui.label('Ви впевнені, що хочете ПЕРЕЗАВАНТАЖИТИ контролер?').classes('text-h6 mb-4')
                    ui.label('Система буде недоступна приблизно 1-2 хвилини.').classes('mb-4 text-gray-500')
                    with ui.row().classes('w-full justify-end gap-4'):
                        ui.button('СКАСУВАТИ', on_click=lambda: diag.submit(False), color='primary')
                        ui.button('ПЕРЕЗАВАНТАЖИТИ', on_click=lambda: diag.submit(True), color='red')

                if await diag:
                    ui.notify('Команда відправлена. До зустрічі через хвилину!', type='negative')
                    reboot_pi()

            ui.button('Перезавантажити Orange Pi', icon='restart_alt', on_click=confirm_reboot).classes(
                'bg-negative text-white shadow-lg')