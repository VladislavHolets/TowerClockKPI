import yaml
from nicegui import ui

from database.crud import create_db_and_tables, init_default_data
from core.scheduler import start_scheduler
from ui.main_layout import create_layout

with open("settings.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

server_host = config["server"]["host"]
server_port = config["server"]["port"]

# ==========================================
# 1. ВЕБ-ІНТЕРФЕЙС
# ==========================================
@ui.page('/')
def index():
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
        title="YADRO | Годинник КПІ",
        dark=False,
        show=False,
        reload=False  # <--- ВИМИКАЄМО АВТОПЕРЕЗАВАНТАЖЕННЯ (КРИТИЧНО ДЛЯ ЗАЛІЗА)
    )