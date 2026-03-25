import datetime
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger  # <--- Додали для разових подій
from apscheduler.schedulers.background import BackgroundScheduler
from database.crud import get_all_events

# Підключаємо наші апаратні модулі
from hardware.motor import step_motor
from hardware.audio import play_hourly_sequence, play_scheduled_event
scheduler = BackgroundScheduler()


def tick_minute():
    """Фоновий процес (викликається рівно на 00 секунді кожної хвилини)"""
    # 1. Отримуємо СПРАВЖНІЙ об'єкт часу для математики
    now = datetime.datetime.now()

    # 2. Робимо окрему текстову змінну для красивого логування
    now_str = now.strftime('%H:%M:%S')
    print(f"[{now_str}] ФОН: Хвилинний тік. -> Відправляємо імпульс на двигун!")

    # 3. Рухаємо стрілки
    step_motor(1)

    # 4. Тепер математика працює ідеально, бо now - це об'єкт datetime
    if now.minute == 0:
        play_hourly_sequence(now.hour)


def execute_audio_event(event_name: str, media_file: str, play_attention: bool):
    """Фоновий процес для подій з БД"""
    now = datetime.datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] Планувальник відправив у чергу подію: '{event_name}'")

    # Ніяких sleep(). Просто кидаємо в чергу. Пріоритетність розбереться сама.
    play_scheduled_event(media_file, play_attention)



# Не забудьте в reload_jobs() додати args=[event.name, event.media_file, event.play_attention]

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
                        args=[event.name, event.media_file,event.play_attention],
                        id=f"event_{event.id}"
                    )
                    print(f"Заплановано разову подію: '{event.name}' на {run_datetime}")

            # --- СТАНДАРТНИЙ CRON ---
            else:
                trigger = CronTrigger.from_crontab(event.cron_expression)
                scheduler.add_job(
                    execute_audio_event,
                    trigger=trigger,
                    args=[event.name, event.media_file,event.play_attention],
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