import os
import sys
import time
import yaml
from database.crud import get_system_settings

with open("settings.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

hw_config = config["hardware"]
STEP_PIN = hw_config.get("motor_step_pin", 0)
DIR_PIN = hw_config.get("motor_dir_pin", 1)
EN_PIN = hw_config.get("motor_en_pin", 2)
INVERT_DIR = hw_config.get("invert_direction", False)

IS_DEV = not os.path.exists('/etc/armbian-release')

if IS_DEV:
    class MockWiringPi:
        def wiringPiSetup(self): pass

        def pinMode(self, pin, mode): pass

        def digitalWrite(self, pin, val): pass


    wiringpi = MockWiringPi()
else:
    if os.getegid() != 0:
        sys.exit('Script must be run as root')
    import wiringpi


def init_motor():
    wiringpi.wiringPiSetup()
    wiringpi.pinMode(DIR_PIN, 1)
    wiringpi.pinMode(STEP_PIN, 1)
    wiringpi.pinMode(EN_PIN, 1)
    wiringpi.digitalWrite(EN_PIN, 0)


def step_motor(minutes: int, fast_calibration: bool = False):
    if minutes == 0:
        return

    settings = get_system_settings()

    # 1. Скільки всього кроків треба зробити
    steps_per_minute = settings.steps_per_minute_dial
    total_steps = abs(minutes) * steps_per_minute

    # 2. Скільки часу має зайняти проходження ОДНІЄЇ хвилини
    duration_per_minute = settings.fast_move_sec if fast_calibration else settings.normal_move_sec

    # 3. МАТЕМАТИКА ЗАЛІЗА: Вираховуємо затримку (delay)
    # Якщо 1 хвилина = 125 кроків, а пройти її треба за 2 секунди,
    # то на 1 крок у нас є: 2 / 125 = 0.016 секунди.
    # Оскільки цикл має дві паузи (HIGH -> пауза -> LOW -> пауза), ділимо ще на 2:
    delay_seconds = (duration_per_minute / steps_per_minute) / 2.0

    is_forward = minutes > 0
    dir_value = 0 if is_forward else 1
    if INVERT_DIR:
        dir_value = 1 if dir_value == 0 else 0

    mode_str = "КАЛІБРУВАННЯ" if fast_calibration else "ХВИЛИННИЙ ТІК"
    print(f"[{mode_str}] Рух на {abs(minutes)} хв ({int(total_steps)} кроків).")
    print(f"Розрахунковий час 1 хвилини: {duration_per_minute}с. Затримка циклу: {delay_seconds:.5f}с")

    # Передаємо сигнал
    wiringpi.digitalWrite(DIR_PIN, dir_value)

    for _ in range(int(total_steps)):
        wiringpi.digitalWrite(STEP_PIN, 1)
        time.sleep(delay_seconds)
        wiringpi.digitalWrite(STEP_PIN, 0)
        time.sleep(delay_seconds)

    print(f"[{mode_str}] Завершено.")