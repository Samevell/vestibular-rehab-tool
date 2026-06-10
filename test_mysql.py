# test_mysql.py
import mysql.connector

try:
    connection = mysql.connector.connect(
        host="127.0.0.1",
        port="3306",
        database="trainer", 
        user="root",
        password="sa"
    )
    print("✅ Подключение успешно!")
    
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"📋 Найдено таблиц: {len(tables)}")
    
    for table in tables:
        print(f"  - {table[0]}")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")