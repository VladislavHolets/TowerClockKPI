import os
import sys
import time
import yaml
import threading
import queue
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

if not IS_DEV:
    init_motor()

# ==========================================
# СИСТЕМА ЧЕРГИ ДЛЯ МОТОРА (ЗАХИСТ ВІД БЛОКУВАННЯ)
# ==========================================
motor_queue = queue.Queue()


def _motor_worker():
    """Безперервний фоновий потік-робітник, який виконує завдання по черзі"""
    while True:
        # Потік "засинає" тут і чекає, поки в черзі не з'явиться завдання
        minutes, fast_calibration = motor_queue.get()
        try:
            _execute_steps(minutes, fast_calibration)
        except Exception as e:
            print(f"[МОТОР ПОМИЛКА] {e}")
        finally:
            # Сповіщаємо чергу, що завдання виконано
            motor_queue.task_done()


# Запускаємо робітника один раз при старті програми
threading.Thread(target=_motor_worker, daemon=True, name="MotorWorker").start()


def _execute_steps(minutes: int, fast_calibration: bool):
    """Справжня взаємодія з залізом (те, що раніше було напряму в step_motor)"""
    settings = get_system_settings()
    if not settings:
        return

    steps_per_minute = settings.steps_per_minute_dial
    total_steps = abs(minutes) * steps_per_minute
    duration_per_minute = settings.fast_move_sec if fast_calibration else settings.normal_move_sec
    delay_seconds = (duration_per_minute / steps_per_minute) / 2.0

    is_forward = minutes > 0
    dir_value = 0 if is_forward else 1
    if INVERT_DIR:
        dir_value = 1 if dir_value == 0 else 0

    mode_str = "КАЛІБРУВАННЯ" if fast_calibration else "ХВИЛИННИЙ ТІК"
    print(f"[{mode_str}] Фізичний рух на {abs(minutes)} хв ({int(total_steps)} кроків).")

    wiringpi.digitalWrite(DIR_PIN, dir_value)

    for _ in range(int(total_steps)):
        wiringpi.digitalWrite(STEP_PIN, 1)
        time.sleep(delay_seconds)
        wiringpi.digitalWrite(STEP_PIN, 0)
        time.sleep(delay_seconds)

    print(f"[{mode_str}] Рух завершено.")


def step_motor(minutes: int, fast_calibration: bool = False):
    """
    БЕЗПЕЧНИЙ ВИКЛИК: миттєво додає завдання в чергу і повертає управління.
    Інтерфейс більше ніколи не зависатиме!
    """
    if minutes == 0:
        return

    # Кладемо кортеж (хвилини, режим) у кошик
    motor_queue.put((minutes, fast_calibration))
    print(f"[МОТОР ЧЕРГА] Додано завдання: {minutes} хв. (В очікуванні: {motor_queue.qsize()})")