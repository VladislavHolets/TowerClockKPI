import yaml
from sqlmodel import SQLModel, Session, create_engine, select
from .models import User, AudioEvent, SystemSetting

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


def init_default_data():
    """Заповнює базу базовими даними при першому запуску."""
    with Session(engine) as session:
        # Перевіряємо, чи є вже глобальні налаштування
        existing_settings = session.exec(select(SystemSetting)).first()
        if not existing_settings:
            # Якщо немає, створюємо їх із значеннями за замовчуванням (з models.py)
            default_settings = SystemSetting()
            session.add(default_settings)

        # Пізніше тут ми додамо створення користувача "admin" за замовчуванням,
        # коли налаштуємо систему хешування паролів.

        session.commit()


# --- Базові функції для роботи з подіями (CRUD) ---

def get_all_events() -> list[AudioEvent]:
    """Повертає весь розклад аудіо подій."""
    with Session(engine) as session:
        events = session.exec(select(AudioEvent)).all()
        return list(events)


def add_audio_event(name: str, cron_expression: str, media_file: str, event_type: str = "bell") -> AudioEvent:
    """Додає нову подію до розкладу."""
    with Session(engine) as session:
        new_event = AudioEvent(
            name=name,
            cron_expression=cron_expression,
            media_file=media_file,
            event_type=event_type
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

def update_audio_event(event_id: int, name: str, cron_expression: str, media_file: str):
    """Оновлює існуючу подію"""
    with Session(engine) as session:
        event = session.get(AudioEvent, event_id)
        if event:
            event.name = name
            event.cron_expression = cron_expression
            event.media_file = media_file
            session.add(event)
            session.commit()

def get_system_settings() -> SystemSetting:
    """Повертає поточні глобальні налаштування."""
    with Session(engine) as session:
        return session.exec(select(SystemSetting)).first()