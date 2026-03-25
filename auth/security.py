import bcrypt

def get_password_hash(password: str) -> str:
    """Перетворює звичайний пароль на хеш для збереження в БД (чистий bcrypt)"""
    # bcrypt працює з байтами, тому конвертуємо рядок у байти
    pwd_bytes = password.encode('utf-8')
    # Генеруємо сіль і сам хеш
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    # Повертаємо як звичайний рядок для збереження в базу
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевіряє, чи збігається введений пароль з хешем у базі"""
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    # Перевіряємо збіг
    return bcrypt.checkpw(pwd_bytes, hash_bytes)