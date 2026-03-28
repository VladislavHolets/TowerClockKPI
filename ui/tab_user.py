from nicegui import ui, app
from database.crud import get_all_users, create_user, delete_user, admin_reset_password


def build_users_tab():
    ui.label('Керування доступом').classes('text-h6 mb-4')

    # ==========================================
    # 1. ДІАЛОГ СТВОРЕННЯ КОРИСТУВАЧА
    # ==========================================
    with ui.dialog() as add_user_dialog, ui.card().classes('min-w-[400px]'):
        ui.label('Створити користувача').classes('text-h6 font-bold')
        new_username = ui.input('Логін').classes('w-full')
        new_password = ui.input('Пароль', password=True).classes('w-full mb-2')
        new_role = ui.select(
            options={'operator': 'Оператор (Тільки керування)', 'admin': 'Адміністратор (Повний доступ)'},
            value='operator',
            label='Рівень доступу'
        ).classes('w-full mb-4')

        def save_new_user():
            if len(new_username.value) < 3 or len(new_password.value) < 4:
                ui.notify('Занадто короткий логін або пароль!', type='warning')
                return
            if create_user(new_username.value, new_password.value, new_role.value):
                ui.notify(f'Користувача {new_username.value} створено!', type='positive')
                add_user_dialog.close()
                users_table.refresh()
            else:
                ui.notify('Користувач з таким логіном вже існує!', type='negative')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Скасувати', on_click=add_user_dialog.close, color='gray')
            ui.button('Створити', on_click=save_new_user, color='primary')

    # ==========================================
    # 2. ВЕРХНЯ ПАНЕЛЬ
    # ==========================================
    with ui.row().classes('w-full justify-between items-center mb-4'):
        ui.label('Список акаунтів системи').classes('text-subtitle1 text-gray-600')
        ui.button('Додати користувача', icon='person_add',
                  on_click=lambda: [new_username.set_value(''), new_password.set_value(''),
                                    add_user_dialog.open()]).classes('bg-accent text-white font-bold')

    # ==========================================
    # 3. ТАБЛИЦЯ КОРИСТУВАЧІВ
    # ==========================================
    @ui.refreshable
    def users_table():
        users = get_all_users()

        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
            {'name': 'username', 'label': 'Логін', 'field': 'username', 'align': 'left'},
            {'name': 'role', 'label': 'Рівень доступу', 'field': 'role_display', 'align': 'left'},
            {'name': 'actions', 'label': 'Дії', 'field': 'actions', 'align': 'center'},
        ]

        rows = [{
            'id': u.id,
            'username': u.username,
            'role_raw': getattr(u, 'role', 'operator'),
            'role_display': 'Адміністратор' if getattr(u, 'role', 'operator') == 'admin' else 'Оператор',
        } for u in users]

        table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full shadow-sm')

        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round size="sm" icon="lock_reset" color="warning" @click="() => $parent.$emit('reset_pass', props.row)" tooltip="Скинути пароль"/>
                <q-btn flat round size="sm" icon="delete" color="negative" @click="() => $parent.$emit('delete', props.row)" tooltip="Видалити"/>
            </q-td>
        ''')

        async def confirm_delete(e):
            row = e.args
            # Захист від видалення самого себе (щоб адмін не відпиляв гілку, на якій сидить)
            if row['username'] == app.storage.user.get('username'):
                ui.notify('Ви не можете видалити власний акаунт!', type='negative')
                return

            with ui.dialog() as diag, ui.card():
                ui.label(f'Видалити користувача {row["username"]}?').classes('text-h6 mb-2')
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('СКАСУВАТИ', color='gray', on_click=lambda: diag.submit(False))
                    ui.button('ТАК, ВИДАЛИТИ', color='negative', on_click=lambda: diag.submit(True))

            if await diag:
                delete_user(row['id'])
                ui.notify('Користувача видалено', type='info')
                users_table.refresh()

        async def reset_pass_dialog(e):
            row = e.args
            with ui.dialog() as diag, ui.card().classes('min-w-[300px]'):
                ui.label(f'Новий пароль для {row["username"]}').classes('text-h6 mb-2')
                new_p = ui.input('Пароль', password=True).classes('w-full mb-4')
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('СКАСУВАТИ', color='gray', on_click=lambda: diag.submit(None))
                    ui.button('ЗБЕРЕГТИ', color='primary', on_click=lambda: diag.submit(new_p.value))

            result = await diag
            if result:
                if len(result) < 4:
                    ui.notify('Пароль занадто короткий!', type='warning')
                else:
                    admin_reset_password(row['id'], result)
                    ui.notify('Пароль успішно змінено!', type='positive')

        table.on('delete', confirm_delete)
        table.on('reset_pass', reset_pass_dialog)

    users_table()