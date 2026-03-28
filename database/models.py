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
    name: str
    cron_expression: str
    media_file: str
    is_active: bool = Field(default=True)
    play_attention: bool = Field(default=False)  # НОВЕ ПОЛЕ: Чи грати attention.mp3 перед цією подією
    volume: int = Field(default=100, ge=0, le=100)

# 3. Таблиця Глобальних Налаштувань (Періоди тиші, гучність)
# Зазвичай тут буде лише один запис (рядок) з id=1
class SystemSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quiet_mode_enabled: bool = Field(default=True)
    global_volume: int = Field(default=80, ge=0, le=100)
    quiet_hours: str = Field(default='[{"start": "24:00", "end": "05:00"}]')
    vol_melody: int = Field(default=100, ge=0, le=100)
    vol_knock: int = Field(default=100, ge=0, le=100)
    vol_attention: int = Field(default=100, ge=0, le=100)
    # НОВЕ ПОЛЕ: Логіка мелодії перед дзвоном ('12_24', 'hourly', 'none')
    pre_chime_mode: str = Field(default="12_24")
    steps_per_minute_dial: int = Field(default=125)
    normal_move_sec: float = Field(default=2.0)
    fast_move_sec: float = Field(default=0.2)
