import os
import time
import threading
import subprocess
import queue
import json
from datetime import datetime
from pathlib import Path
from database.crud import get_system_settings

IS_DEV = not os.path.exists('/etc/armbian-release')
MEDIA_FOLDER = Path("storage/media")

# ==========================================
# СИСТЕМА ПРІОРИТЕТІВ (Менше число = вищий пріоритет)
# ==========================================
PRIORITY_SYSTEM_CHIME = 1
PRIORITY_USER_EVENT = 5
PRIORITY_TEST = 10

audio_queue = queue.PriorityQueue()
abort_flag = False

if IS_DEV:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    import pygame

    pygame.mixer.init()


def is_quiet_time() -> bool:
    settings = get_system_settings()
    if not settings or not settings.quiet_mode_enabled:
        return False

    now = datetime.now().time()
    try:
        qh_list = json.loads(settings.quiet_hours)
    except Exception:
        return False

    for qh in qh_list:
        try:
            start = datetime.strptime(qh.get('start', '00:00'), "%H:%M").time()
            end = datetime.strptime(qh.get('end', '00:00'), "%H:%M").time()

            if start <= end:
                if start <= now <= end:
                    return True
            else:
                if start <= now or now <= end:
                    return True
        except Exception:
            continue

    return False

def _play_file_raw(filename: str, volume: int = 100):
    """Фізичне відтворення файлу (без замків, бо працює в одному потоці-робітнику)"""
    global abort_flag
    if abort_flag or is_quiet_time():
        return

    filepath = MEDIA_FOLDER / filename
    if not filepath.exists():
        print(f"[АУДІО ПОМИЛКА] Файл не знайдено: {filepath}")
        return

    if IS_DEV:
        print(f"[АУДІО DEV] Відтворюю: {filename} (Гучність: {volume}%)")
        try:
            pygame.mixer.music.set_volume(volume / 100.0)
            pygame.mixer.music.load(str(filepath))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if abort_flag:
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.1)
            if hasattr(pygame.mixer.music, 'unload'):
                pygame.mixer.music.unload()
        except Exception as e:
            print(f"[АУДІО ПОМИЛКА] {e}")
    else:
        print(f"[АУДІО PROD] mpv відтворює: {filename}")
        try:
            process = subprocess.Popen(
                ["mpv", "--quiet", "--no-video", "--volume-max=100", f"--volume={volume}", str(filepath)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            while process.poll() is None:
                if abort_flag:
                    process.terminate()
                    break
                time.sleep(0.1)
        except Exception as e:
            print(f"[АУДІО ПОМИЛКА mpv] {e}")


def _worker_process_task(task_type, args):
    """Розшифровує завдання з черги і запускає його частини"""
    global abort_flag
    abort_flag = False

    if task_type == 'hourly_chime':
        current_hour_24 = args[0]
        settings = get_system_settings()
        mode = settings.pre_chime_mode if settings else "12_24"
        vol_melody = settings.vol_melody if settings else 100
        vol_knock = settings.vol_knock if settings else 100
        if mode == 'hourly' or (mode == '12_24' and current_hour_24 in [0, 12]):
            print(f"[ОРКЕСТРАТОР] Граємо переддзвін (Режим: {mode}Гучність: {vol_melody}%)")
            _play_file_raw("melody.mp3",vol_melody)

        knocks_count = 12 if current_hour_24 % 12 == 0 else current_hour_24 % 12
        print(f"[ОРКЕСТРАТОР] Відбиваємо дзвони: {knocks_count} ударів (Гучність: {vol_knock}%).")
        for _ in range(knocks_count):
            if abort_flag: break
            _play_file_raw("knock.mp3",vol_knock)
            for _ in range(5):
                if abort_flag: break
                time.sleep(0.1)

    elif task_type == 'scheduled_event':
        media_file, play_attention,volume = args
        if play_attention:
            _play_file_raw("attention.mp3",get_system_settings().vol_attention)
        _play_file_raw(media_file,volume)

    elif task_type == 'test_audio':
        _play_file_raw("attention.mp3",get_system_settings().vol_attention)

    elif task_type == 'test_file':
        filename, volume = args
        _play_file_raw(filename, volume)


def _audio_worker():
    """Фоновий робітник: розгрібає чергу строго за пріоритетами"""
    while True:
        # Чекаємо, поки в черзі з'явиться хоча б 1 завдання
        while audio_queue.empty():
            time.sleep(0.1)

        # ПАТЕРН "ВІКНО АГРЕГАЦІЇ" (Aggregation Window)
        # Даємо планувальнику 0.2 сек, щоб він встиг закинути ВСІ задачі,
        # які спрацювали в цю ж мілісекунду. Черга сама їх відсортує.
        time.sleep(0.2)

        # Витягуємо найважливіше завдання: (priority, timestamp, task_type, args)
        priority, timestamp, task_type, args = audio_queue.get()

        try:
            #if not abort_flag:
            _worker_process_task(task_type, args)
        except Exception as e:
            print(f"[АУДІО ПОМИЛКА РОБІТНИКА] {e}")
        finally:
            audio_queue.task_done()


# Запускаємо робітника один раз при старті
threading.Thread(target=_audio_worker, daemon=True, name="AudioWorker").start()


# ==========================================
# ПУБЛІЧНІ ФУНКЦІЇ ДЛЯ ІНШИХ МОДУЛІВ
# ==========================================

def play_hourly_sequence(current_hour_24: int):
    # Додаємо час створення (time.time()), щоб задачі з однаковим пріоритетом виконувалися по черзі
    audio_queue.put((PRIORITY_SYSTEM_CHIME, time.time(), 'hourly_chime', (current_hour_24,)))


def play_scheduled_event(media_file: str, play_attention: bool,volume: int = 100):
    audio_queue.put((PRIORITY_USER_EVENT, time.time(), 'scheduled_event', (media_file, play_attention, volume)))


def play_test_audio():
    audio_queue.put((PRIORITY_TEST, time.time(), 'test_audio', ()))

# Додаємо нову:
def play_test_file(filename: str, volume: int):
    audio_queue.put((PRIORITY_TEST, time.time(), 'test_file', (filename, volume)))

def stop_audio():
    global abort_flag
    abort_flag = True
    print("[АУДІО] ПРИМУСОВА ЗУПИНКА! Очищаємо чергу...")

    # Очищаємо всі заплановані звуки, які ще не почали грати
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
            audio_queue.task_done()
        except queue.Empty:
            break

