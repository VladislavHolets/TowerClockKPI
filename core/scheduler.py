import datetime
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger  # <--- Додали для разових подій
from apscheduler.schedulers.background import BackgroundScheduler
from database.crud import get_all_events

# Підключаємо наші апаратні модулі
from hardware.motor import step_motor
from hardware.audio import play_audio

scheduler = BackgroundScheduler()


def tick_minute():
    """Ця функція викликається рівно на 00 секунді кожної хвилини."""
    now = datetime.datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] ФОН: Хвилинний тік. -> Відправляємо імпульс на кроковий двигун!")

    # Викликаємо реальний рух (1 хвилина вперед)
    step_motor(1)


def execute_audio_event(event_name: str, media_file: str):
    """Ця функція викликається, коли настає час для аудіо події з БД."""
    now = datetime.datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] ФОН: Настав час для події '{event_name}'")

    # Передаємо файл у драйвер (він сам перевірить період тиші)
    play_audio(media_file)


def reload_jobs():
    """Очищає розклад і завантажує його наново з бази даних."""
    scheduler.remove_all_jobs()

    # 1. Базова залізна задача - тік кожну хвилину (спрацьовує рівно на 00 секунді)
    scheduler.add_job(tick_minute, 'cron', second='0', id='hardware_minute_tick')

    # 2. Динамічні задачі - завантажуємо аудіо події з БД
    events = get_all_events()
    for event in events:
        if not event.is_active:
            continue

        try:
            # --- РОЗШИФРОВКА РАЗОВИХ ПОДІЙ (DATE) ---
            if event.cron_expression.startswith("DATE:"):
                date_str = event.cron_expression.replace("DATE:", "")
                run_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")

                # Захист: плануємо тільки якщо дата ще не минула
                if run_datetime > datetime.datetime.now():
                    scheduler.add_job(
                        execute_audio_event,
                        trigger=DateTrigger(run_date=run_datetime),
                        args=[event.name, event.media_file],
                        id=f"event_{event.id}"
                    )
                    print(f"Заплановано разову подію: '{event.name}' на {run_datetime}")

            # --- СТАНДАРТНИЙ CRON ---
            else:
                trigger = CronTrigger.from_crontab(event.cron_expression)
                scheduler.add_job(
                    execute_audio_event,
                    trigger=trigger,
                    args=[event.name, event.media_file],
                    id=f"event_{event.id}"
                )
                print(f"Заплановано регулярну подію: '{event.name}' [{event.cron_expression}]")

        except Exception as e:
            print(f"Помилка планування події '{event.name}': {e}")


def start_scheduler():
    """Запускає серце годинника"""
    reload_jobs()
    scheduler.start()
    print("Планувальник успішно запущено! Чекаємо початку наступної хвилини...")