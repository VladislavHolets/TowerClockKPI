import subprocess
import os

from nicegui import ui

IS_DEV = not os.path.exists('/etc/armbian-release')

def reboot_pi():
    """Перезавантажує контролер (потрібні права root)"""
    if IS_DEV:
        ui.notify('СИСТЕМА: Команда reboot проігнорована (Режим розробки)', type='info')
        print("[SYSTEM] Режим розробки: імітація перезавантаження...")
        return
    try:
        # Команда reboot вимагає права sudo.
        # Якщо скрипт запущено від root, спрацює миттєво.
        subprocess.run(["sudo", "reboot"], check=True)
    except Exception as e:
        print(f"Помилка перезавантаження: {e}")

def update_wifi_settings(ssid: str, password: str):
    """Змінює назву та пароль існуючої точки доступу Hotspot"""
    """Змінює налаштування Hotspot через nmcli (тільки на Linux)"""
    if IS_DEV:
        ui.notify(f'СИСТЕМА: Wi-Fi SSID "{ssid}" збережено (Режим розробки)', type='info')
        print(f"[SYSTEM] Режим розробки: імітація зміни Wi-Fi на {ssid}")
        return True

    try:
        # 1. Змінюємо SSID (назву мережі)
        subprocess.run(["sudo", "nmcli", "connection", "modify", "Hotspot", "802-11-wireless.ssid", ssid], check=True)
        # 2. Змінюємо пароль
        subprocess.run(["sudo", "nmcli", "connection", "modify", "Hotspot", "802-11-wireless-security.psk", password], check=True)
        # 3. Перезапускаємо з'єднання, щоб зміни вступили в дію
        subprocess.run(["sudo", "nmcli", "connection", "down", "Hotspot"], check=True)
        subprocess.run(["sudo", "nmcli", "connection", "up", "Hotspot"], check=True)
        return True
    except Exception as e:
        print(f"Помилка Wi-Fi: {e}")
        return False