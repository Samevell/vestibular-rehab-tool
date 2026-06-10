# test_tables.py
from database import Database

db = Database()

# Пытаемся подключиться
if db.connect():
    print("✅ Подключение успешно!")
    
    # Проверяем таблицы
    db.check_tables()
    
    # Пытаемся создать пользователя
    user_id = db.get_or_create_user("Тест1", "Пользователь")
    print(f"ID пользователя: {user_id}")
    
    db.close()
else:
    print("❌ Не удалось подключиться к БД")