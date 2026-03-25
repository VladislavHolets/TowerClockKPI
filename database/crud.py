import yaml
from sqlmodel import SQLModel, Session, create_engine, select
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

def verify_user(username: str, plain_password: str) -> bool:
    """Перевіряє логін і пароль під час входу в систему"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return False
        return verify_password(plain_password, user.hashed_password)

def update_user_password(username: str, new_password: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
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
def add_audio_event(name: str, cron_expression: str, media_file: str, event_type: str = "bell", play_attention: bool = False) -> AudioEvent:
    """Додає нову подію до розкладу."""
    with Session(engine) as session:
        new_event = AudioEvent(
            name=name,
            cron_expression=cron_expression,
            media_file=media_file,
            event_type=event_type,
            play_attention=play_attention  # Зберігаємо галочку гонгу
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

# ОНОВЛЕНО: додано параметр play_attention
def update_audio_event(event_id: int, name: str, cron_expression: str, media_file: str, play_attention: bool):
    """Оновлює існуючу подію"""
    with Session(engine) as session:
        event = session.get(AudioEvent, event_id)
        if event:
            event.name = name
            event.cron_expression = cron_expression
            event.media_file = media_file
            event.play_attention = play_attention  # Оновлюємо галочку гонгу
            session.add(event)
            session.commit()

def get_system_settings() -> SystemSetting:
    """Повертає поточні глобальні налаштування."""
    with Session(engine) as session:
        return session.exec(select(SystemSetting)).first()