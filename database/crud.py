from typing import Any

import yaml
from sqlmodel import SQLModel, Session, create_engine, select, text, inspect
from .models import User, AudioEvent, SystemSetting
from auth.security import get_password_hash, verify_password

# 1. Читаємо шлях до БД з нашого конфігу
with open("settings.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

sqlite_url = config["paths"]["db_url"]

# Створюємо "двигун" бази даних.
# connect_args={"check_same_thread": False} потрібен для SQLite у багатопотокових веб-застосунках
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Створює файл бази даних та всі таблиці, якщо їх ще не існує."""
    SQLModel.metadata.create_all(engine)
    run_auto_migrations()


def run_auto_migrations():
    """Динамічно перевіряє БД і автоматично додає відсутні колонки."""
    inspector = inspect(engine)

    with Session(engine) as session:
        # Проходимося по всіх таблицях, які ми описали в models.py
        for table_name, table_obj in SQLModel.metadata.tables.items():

            # Якщо таблиці ще немає в базі - пропускаємо (її створить create_all)
            if not inspector.has_table(table_name):
                continue

            # Отримуємо список колонок, які вже існують у фізичному файлі БД
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]

            # Перевіряємо кожну колонку з нашого Python-коду
            for column in table_obj.columns:
                if column.name not in existing_columns:
                    # Дістаємо правильний SQL-тип колонки (напр. VARCHAR, INTEGER, BOOLEAN)
                    col_type = column.type.compile(engine.dialect)

                    # Формуємо і виконуємо запит автоматично!
                    query = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"

                    try:
                        session.execute(text(query))
                        print(
                            f"[АВТОМІГРАЦІЯ] Успішно додано відсутню колонку '{column.name}' у таблицю '{table_name}'")
                    except Exception as e:
                        print(f"[АВТОМІГРАЦІЯ] Помилка додавання '{column.name}': {e}")

        session.commit()

def init_default_data():
    """Заповнює базу базовими даними та створює адміна при першому запуску."""
    with Session(engine) as session:
        # 1. Глобальні налаштування
        existing_settings = session.exec(select(SystemSetting)).first()
        if not existing_settings:
            session.add(SystemSetting())

        # 2. Створення адміністратора за замовчуванням (якщо його ще немає)
        existing_admin = session.exec(select(User).where(User.username == "admin")).first()
        if not existing_admin:
            print("[АВТОРИЗАЦІЯ] Створюю користувача 'admin' з паролем 'admin123'")
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            session.add(admin_user)

        session.commit()

def verify_user(username: str, plain_password: str) -> bool | None | Any:
    """Перевіряє логін і пароль під час входу в систему"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return False
        elif verify_password(plain_password, user.hashed_password):
            return user
        return None


def update_user_password(username: str, new_password: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            user.hashed_password = get_password_hash(new_password)
            session.add(user)
            session.commit()
            return True
    return False

def get_all_users() -> list[User]:
    """Повертає список всіх користувачів."""
    with Session(engine) as session:
        return list(session.exec(select(User)).all())

def create_user(username: str, plain_password: str, role: str = "operator") -> bool:
    """Створює нового користувача. Повертає False, якщо логін вже зайнятий."""
    with Session(engine) as session:
        if session.exec(select(User).where(User.username == username)).first():
            return False
        new_user = User(
            username=username,
            hashed_password=get_password_hash(plain_password),
            role=role
        )
        session.add(new_user)
        session.commit()
        return True

def delete_user(user_id: int):
    """Видаляє користувача за ID."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()

def admin_reset_password(user_id: int, new_password: str) -> bool:
    """Примусове скидання пароля адміністратором."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            user.hashed_password = get_password_hash(new_password)
            session.add(user)
            session.commit()
            return True
        return False
# --- Базові функції для роботи з подіями (CRUD) ---

def get_all_events() -> list[AudioEvent]:
    """Повертає весь розклад аудіо подій."""
    with Session(engine) as session:
        events = session.exec(select(AudioEvent)).all()
        return list(events)


# ОНОВЛЕНО: додано параметр play_attention
def add_audio_event(name: str, cron_expression: str, media_file: str, event_type: str = "bell", play_attention: bool = False, volume: int = 100) -> AudioEvent:
    """Додає нову подію до розкладу із заданою гучністю."""
    with Session(engine) as session:
        new_event = AudioEvent(
            name=name,
            cron_expression=cron_expression,
            media_file=media_file,
            event_type=event_type,
            play_attention=play_attention,
            volume=volume  # Зберігаємо індивідуальну гучність
        )
        session.add(new_event)
        session.commit()
        session.refresh(new_event)
        return new_event

def toggle_audio_event(event_id: int):
    """Змінює статус події (Активно <-> Пауза)"""
    with Session(engine) as session:
        event = session.get(AudioEvent, event_id)
        if event:
            event.is_active = not event.is_active
            session.add(event)
            session.commit()
            return event.is_active

def delete_audio_event(event_id: int):
    """Видаляє подію з бази"""
    with Session(engine) as session:
        event = session.get(AudioEvent, event_id)
        if event:
            session.delete(event)
            session.commit()

def update_audio_event(event_id: int, name: str, cron_expression: str, media_file: str, play_attention: bool, volume: int = 100):
    """Оновлює існуючу подію."""
    with Session(engine) as session:
        event = session.get(AudioEvent, event_id)
        if event:
            event.name = name
            event.cron_expression = cron_expression
            event.media_file = media_file
            event.play_attention = play_attention
            event.volume = volume
            session.add(event)
            session.commit()

def get_system_settings() -> SystemSetting:
    """Повертає поточні глобальні налаштування."""
    with Session(engine) as session:
        return session.exec(select(SystemSetting)).first()