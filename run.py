import yaml
from docutils.nodes import title
from nicegui import ui, app

from database.crud import create_db_and_tables, init_default_data
from core.scheduler import start_scheduler
from ui.login import build_login_page
from ui.main_layout import create_layout

with open("settings.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

server_host = config["server"]["host"]
server_port = config["server"]["port"]
secret_key = config["server"]["secret_key"]
title = config["server"]["title"]
# ==========================================
# 1. ВЕБ-ІНТЕРФЕЙС
# ==========================================
# 1. Відкрита сторінка логіну
@ui.page('/login')
def login_page():
    build_login_page()


# 2. Захищена головна сторінка
@ui.page('/')
def index_page():
    # Перевіряємо, чи є в користувача "ключ" у сесії
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    # Якщо авторизований — малюємо інтерфейс
    create_layout()
# ==========================================
# 2. ЗАПУСК ДОДАТКУ ТА ФОНОВИХ ПРОЦЕСІВ
# ==========================================
if __name__ in {"__main__", "__mp_main__"}:
    print("Ініціалізація бази даних...")
    create_db_and_tables()
    init_default_data()

    print("Запуск фонового планувальника...")
    start_scheduler()

    print(f"Запуск веб-сервера на http://{server_host}:{server_port}")
    ui.run(
        host=server_host,
        port=server_port,
        title=title,
        storage_secret=secret_key,
        dark=False,
        show=False,
        reload=False  # <--- ВИМИКАЄМО АВТОПЕРЕЗАВАНТАЖЕННЯ (КРИТИЧНО ДЛЯ ЗАЛІЗА)
    )