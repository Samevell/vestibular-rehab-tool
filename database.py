import mysql.connector
from mysql.connector import Error
from datetime import datetime
import traceback  # Добавляем для детальной отладки
import threading

from db_config import mysql_connect_kwargs
class Database:
    def __init__(self):
        self.connection = None
        self.lock = threading.Lock()
        print("✅ Database инициализирован")
    
    def connect(self):
        """Подключение к БД (вызывается только когда нужно)"""
        if self.connection and self.connection.is_connected():
            print("⚠️ Соединение уже установлено")
            return True
        
        try:
            print("🔄 Попытка подключения к MySQL...")
            self.connection = mysql.connector.connect(
                **mysql_connect_kwargs(),
            )
            print("✅ Успешное подключение к MySQL")
            
            # Проверяем существование таблиц
            self.check_tables()
            return True
            
        except Error as e:
            print(f"❌ Ошибка подключения к MySQL: {e}")
            traceback.print_exc()  # Печатаем полный traceback
            self.connection = None
            return False
    
    def check_tables(self):
        """Проверка существования таблиц"""
        if not self.connection:
            print("❌ Нет соединения для проверки таблиц")
            return False
        
        cursor = self.connection.cursor()
        try:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 Найдено таблиц: {len(tables)}")
            
            if len(tables) == 0:
                print("⚠️ Таблицы не найдены, создаем...")
                return self.create_tables()
            else:
                print("✅ Таблицы существуют:")
                for table in tables:
                    print(f"  - {table[0]}")
                return True
                
        except Error as e:
            print(f"❌ Ошибка при проверке таблиц: {e}")
            return False
        finally:
            cursor.close()
            
    def delete_user(self, user_id):
        with self.lock:
            try:
                if not self._ensure_connection():
                    return False
                
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                self.connection.commit()
                cursor.close()
                return True
            except Exception as e:
                print(e)
                return False
    def create_tables(self):
        """Создание таблиц (только при активном соединении)"""
        if not self.connection:
            print("❌ Нет соединения с БД для создания таблиц")
            return False
        
        cursor = self.connection.cursor()
        
        try:
            print("🔄 Создание таблиц...")
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_user (first_name, last_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✅ Таблица 'users' создана")
            
            # Таблица для упражнения 1
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_1_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    seconds_per_apple INT NOT NULL,
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✅ Таблица 'exercise_1_results' создана")
            
            # Таблица для упражнения 2
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_2_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    seconds_per_apple INT NOT NULL,
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✅ Таблица 'exercise_2_results' создана")
            
            # Таблица для упражнения 3
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_3_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    speed VARCHAR(20) NOT NULL,
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✅ Таблица 'exercise_3_results' создана")
            
            self.connection.commit()
            print("🎉 Все таблицы успешно созданы!")
            return True
            
        except Error as e:
            print(f"❌ Ошибка при создании таблиц: {e}")
            traceback.print_exc()
            return False
        finally:
            cursor.close()
    
    def get_or_create_user(self, first_name, last_name):
        """Получение или создание пользователя"""
        print(f"🔄 Получение/создание пользователя: {first_name} {last_name}")
        
        # Убеждаемся, что соединение установлено
        if not self.connect():
            print("❌ Не удалось подключиться к БД")
            return None
        
        if not self.connection:
            print("❌ Нет соединения с БД")
            return None
        
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Проверяем существование пользователя
            cursor.execute(
                "SELECT id FROM users WHERE first_name = %s AND last_name = %s",
                (first_name, last_name)
            )
            
            user = cursor.fetchone()
            
            if user:
                print(f"✅ Найден существующий пользователь (ID: {user['id']})")
                return user['id']
            else:
                # Создаем нового пользователя
                print(f"🔄 Создание нового пользователя...")
                cursor.execute(
                    "INSERT INTO users (first_name, last_name) VALUES (%s, %s)",
                    (first_name, last_name)
                )
                self.connection.commit()
                user_id = cursor.lastrowid
                print(f"✅ Создан пользователь: {first_name} {last_name} (ID: {user_id})")
                return user_id
                
        except Error as e:
            print(f"❌ Ошибка при работе с пользователем: {e}")
            traceback.print_exc()
            return None
        finally:
            if cursor:
                cursor.close()
    
    def save_exercise_1(self, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score):
        """Сохранение результатов упражнения 1"""
        return self._save_exercise("exercise_1_results", user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score, "1")
    
    def save_exercise_2(self, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score):
        """Сохранение результатов упражнения 2"""
        return self._save_exercise("exercise_2_results", user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score, "2")
    
    def save_exercise_3(self, user_id, apples_count, speed, background, caught_apples, coefficient, total_score):
        """Сохранение результатов упражнения 3"""
        print(f"🔄 Сохранение упражнения 3 для пользователя {user_id}")
        
        if not self.connect():
            print("❌ Не удалось подключиться к БД")
            return False
        
        if not self.connection or user_id is None:
            print("❌ Невозможно сохранить результат упражнения 3")
            return False
        
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO exercise_3_results 
                (user_id, apples_count, speed, background, caught_apples, coefficient, total_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, apples_count, speed, background, caught_apples, coefficient, total_score))
            self.connection.commit()
            print(f"✅ Сохранен результат упражнения 3 для пользователя {user_id}")
            return True
        except Error as e:
            print(f"❌ Ошибка при сохранении упражнения 3: {e}")
            traceback.print_exc()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def _save_exercise(self, table_name, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score, ex_num):
        """Общий метод для сохранения упражнений 1 и 2"""
        print(f"🔄 Сохранение упражнения {ex_num} для пользователя {user_id}")
        
        if not self.connect():
            print(f"❌ Не удалось подключиться к БД для упражнения {ex_num}")
            return False
        
        if not self.connection or user_id is None:
            print(f"❌ Невозможно сохранить результат упражнения {ex_num}")
            return False
        
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"""
                INSERT INTO {table_name} 
                (user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score))
            self.connection.commit()
            print(f"✅ Сохранен результат упражнения {ex_num} для пользователя {user_id}")
            return True
        except Error as e:
            print(f"❌ Ошибка при сохранении упражнения {ex_num}: {e}")
            traceback.print_exc()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ Соединение с БД закрыто")

    def get_all_users(self):
        """Получение всех пользователей из БД"""
        print("🔄 Получение всех пользователей...")
        
        if not self.connect():
            print("❌ Не удалось подключиться к БД")
            return []
        
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, first_name, last_name 
                FROM users 
                ORDER BY last_name, first_name
            """)
            users = cursor.fetchall()
            print(f"✅ Получено пользователей: {len(users)}")
            return users
        except Error as e:
            print(f"❌ Ошибка при получении пользователей: {e}")
            traceback.print_exc()
            return []
        finally:
            if cursor:
                cursor.close()

    def get_exercise_history(self, exercise_type, limit=100):
            """Получение истории упражнений"""
            print(f"🔄 Получение истории упражнения {exercise_type}...")
            
            if not self.connect():
                print("❌ Не удалось подключиться к БД")
                return []
            
            cursor = None
            try:
                cursor = self.connection.cursor(dictionary=True)
                
                if exercise_type == 1:
                    cursor.execute("""
                        SELECT 
                            e1.id,
                            'Упражнение 1' as exercise_type,
                            e1.exercise_date,
                            CONCAT(u.first_name, ' ', u.last_name) as user_name,
                            e1.apples_count,
                            e1.caught_apples,
                            CONCAT(e1.seconds_per_apple, ' сек') as difficulty,
                            e1.coefficient,
                            e1.total_score
                        FROM exercise_1_results e1
                        JOIN users u ON e1.user_id = u.id
                        ORDER BY e1.exercise_date DESC
                        LIMIT %s
                    """, (limit,))
                    
                elif exercise_type == 2:
                    cursor.execute("""
                        SELECT 
                            e2.id,
                            'Упражнение 2' as exercise_type,
                            e2.exercise_date,
                            CONCAT(u.first_name, ' ', u.last_name) as user_name,
                            e2.apples_count,
                            e2.caught_apples,
                            CONCAT(e2.seconds_per_apple, ' сек') as difficulty,
                            e2.coefficient,
                            e2.total_score
                        FROM exercise_2_results e2
                        JOIN users u ON e2.user_id = u.id
                        ORDER BY e2.exercise_date DESC
                        LIMIT %s
                    """, (limit,))
                    
                elif exercise_type == 3:
                    cursor.execute("""
                        SELECT 
                            e3.id,
                            'Упражнение 3' as exercise_type,
                            e3.exercise_date,
                            CONCAT(u.first_name, ' ', u.last_name) as user_name,
                            e3.apples_count,
                            e3.caught_apples,
                            e3.speed as difficulty,
                            e3.coefficient,
                            e3.total_score
                        FROM exercise_3_results e3
                        JOIN users u ON e3.user_id = u.id
                        ORDER BY e3.exercise_date DESC
                        LIMIT %s
                    """, (limit,))
                
                records = cursor.fetchall()
                print(f"✅ Получено записей упражнения {exercise_type}: {len(records)}")
                return records
                
            except Error as e:
                print(f"❌ Ошибка при получении истории упражнения {exercise_type}: {e}")
                traceback.print_exc()
                return []
            finally:
                if cursor:
                    cursor.close()