from typing import Optional
from sqlmodel import Field, SQLModel


# 1. Таблиця Користувачів (для авторизації)
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="operator")  # Ролі: "admin" (повний доступ) або "operator" (тільки керування)


# 2. Таблиця Розкладу Аудіо (Дзвінки, гімни, оголошення)
class AudioEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Наприклад: "Щогодинний дзвін", "Гімн 1 вересня"
    event_type: str = Field(default="bell")  # Тип події: "bell", "announcement", "anthem"

    # Використовуємо формат cron (хвилина, година, день, місяць, день тижня)
    # Це ідеально лягає на логіку APScheduler
    cron_expression: str  # Наприклад: "0 * * * *" (щогодини), "0 12 * * *" (о 12:00)

    media_file: str  # Назва файлу в папці storage/media, напр. "bell.mp3"
    is_active: bool = Field(default=True)  # Можливість тимчасово вимкнути подію без видалення


# 3. Таблиця Глобальних Налаштувань (Періоди тиші, гучність)
# Зазвичай тут буде лише один запис (рядок) з id=1
class SystemSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quiet_mode_enabled: bool = Field(default=True)
    quiet_start: str = Field(default="22:00")  # Формат ГГ:ХХ
    quiet_end: str = Field(default="07:00")  # Формат ГГ:ХХ
    global_volume: int = Field(default=80, ge=0, le=100)  # Гучність від 0 до 100

    # --- ЛЮДЯНІ НАЛАШТУВАННЯ МЕХАНІКИ ---
    # Передаточне число шестерень (скільки кроків двигуна = 1 хвилина на циферблаті)
    steps_per_minute_dial: int = Field(default=125)

    # Скільки фізичних секунд має тривати рух стрілки на 1 хвилину
    normal_move_sec: float = Field(default=2.0)  # Для звичайного ходу (напр. 2 секунди)
    fast_move_sec: float = Field(default=0.2)