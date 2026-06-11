# database_preconnected.py
import json
import mysql.connector
from mysql.connector import Error
import threading
import traceback

from db_config import mysql_connect_kwargs

EXERCISE_TABLES = {
    1: "exercise_1_results",
    2: "exercise_2_results",
    3: "exercise_3_results",
    4: "exercise_4_results",
    5: "exercise_5_results",
    6: "exercise_6_results",
    7: "exercise_7_results",
    8: "exercise_8_results",
    9: "exercise_9_results",
}

EXERCISE_HISTORY_QUERIES = [
    ("exercise_1_results", "e1", "Упражнение 1", "CONCAT(e1.seconds_per_apple, ' сек')"),
    ("exercise_2_results", "e2", "Упражнение 2", "CONCAT(e2.seconds_per_apple, ' сек')"),
    ("exercise_3_results", "e3", "Упражнение 3", "e3.speed"),
    ("exercise_4_results", "e4", "Упражнение 4", "e4.param3"),
    ("exercise_5_results", "e5", "Упражнение 5", "e5.param3"),
    ("exercise_6_results", "e6", "Упражнение 6", "CONCAT(e6.time_sec, ' сек')"),
    ("exercise_7_results", "e7", "Упражнение 7", "e7.param3"),
    ("exercise_8_results", "e8", "Упражнение 8", "CONCAT(e8.speed, ' / ', e8.color_interval, 'с')"),
    ("exercise_9_results", "e9", "Упражнение 9", "e9.param3"),
]

class DatabasePreconnected:
    """БД с предварительным подключением при инициализации"""
    
    def __init__(self):
        self.connection = None
        self.lock = threading.Lock()
        self.is_connected = False
        
        print("🔄 Инициализация DatabasePreconnected...")
        
        # Пытаемся подключиться сразу при создании объекта
        self._initial_connect()
    
    def _initial_connect(self):
        """Предварительное подключение при инициализации"""
        try:
            print("🔄 Предварительное подключение к MySQL...")
            
            self.connection = mysql.connector.connect(
                **mysql_connect_kwargs(),
                autocommit=True,
                pool_size=1,
                connect_timeout=5,
            )
            
            if self.connection.is_connected():
                self.is_connected = True
                print("✅ Предварительное подключение успешно!")
                
                # Проверяем таблицы
                self._check_tables()
                
            else:
                print("❌ Подключение не установлено")
                self.is_connected = False
                
        except Error as e:
            print(f"❌ Ошибка предварительного подключения: {e}")
            self.is_connected = False
            self.connection = None
        except Exception as e:
            print(f"❌ Неизвестная ошибка при подключении: {e}")
            self.is_connected = False
            self.connection = None
    
    def _check_tables(self):
        """Проверка существования таблиц"""
        if not self.is_connected:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 Найдено таблиц: {len(tables)}")
            cursor.close()
            
            if len(tables) == 0:
                print("⚠️ Таблицы не найдены, создание будет при первом запросе")

            self._ensure_doctor_baseline_table()
            self._ensure_exercise_tables()
                
        except Error as e:
            print(f"⚠️ Ошибка при проверке таблиц: {e}")

    def _ensure_doctor_baseline_table(self, cursor=None):
        """Создаёт таблицу назначений врача, если её ещё нет."""
        close_cursor = False
        if cursor is None:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            close_cursor = True
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS doctor_baseline (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    exercise_id INT NOT NULL,
                    params_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_exercise (user_id, exercise_id)
                )
            """)
            if close_cursor:
                self.connection.commit()
            return True
        except Error as e:
            print(f"⚠️ Не удалось создать doctor_baseline: {e}")
            return False
        finally:
            if close_cursor:
                cursor.close()

    def _ensure_exercise_tables(self, cursor=None):
        """Создаёт таблицы результатов упражнений 4–9, если их ещё нет."""
        close_cursor = False
        if cursor is None:
            if not self._ensure_connection():
                return False
            cursor = self.connection.cursor()
            close_cursor = True
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_4_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    time_sec FLOAT NOT NULL,
                    param3 VARCHAR(50),
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_5_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    time_sec FLOAT NOT NULL,
                    param3 VARCHAR(50),
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_6_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    time_sec FLOAT NOT NULL,
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_7_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    time_sec FLOAT NOT NULL,
                    param3 VARCHAR(50),
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_8_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    time_sec FLOAT NOT NULL,
                    color_interval FLOAT NOT NULL,
                    speed VARCHAR(50),
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_9_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    apples_count INT NOT NULL,
                    time_sec FLOAT NOT NULL,
                    param3 VARCHAR(50),
                    background VARCHAR(50),
                    caught_apples INT NOT NULL,
                    coefficient FLOAT NOT NULL,
                    total_score FLOAT NOT NULL,
                    exercise_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            if close_cursor:
                self.connection.commit()
            return True
        except Error as e:
            print(f"⚠️ Не удалось создать таблицы упражнений 4–9: {e}")
            return False
        finally:
            if close_cursor:
                cursor.close()

    def _get_existing_table_names(self):
        cursor = self.connection.cursor()
        cursor.execute("SHOW TABLES")
        names = {row[0] for row in cursor.fetchall()}
        cursor.close()
        return names
    
    def _ensure_connection(self):
        """Убедиться, что соединение активно"""
        if not self.is_connected or not self.connection or not self.connection.is_connected():
            print("⚠️ Соединение разорвано, пытаемся переподключиться...")
            self._initial_connect()
        
        return self.is_connected
    
    def connect(self):
        """Публичный метод для подключения (совместимость с DatabaseSync)"""
        return self._ensure_connection()
    
    def get_or_create_user(self, first_name, last_name):
        """Получение или создание пользователя"""
        print(f"🔄 Создание пользователя: {first_name} {last_name}")
        
        with self.lock:
            try:
                # Проверяем соединение
                if not self._ensure_connection():
                    print("❌ Нет соединения с БД")
                    return None
                
                cursor = self.connection.cursor(dictionary=True)
                
                # Проверяем существование пользователя
                cursor.execute(
                    "SELECT id FROM users WHERE first_name = %s AND last_name = %s",
                    (first_name, last_name)
                )
                
                user = cursor.fetchone()
                
                if user:
                    print(f"✅ Найден пользователь ID: {user['id']}")
                    result = user['id']
                else:
                    # Создаем нового пользователя
                    cursor.execute(
                        "INSERT INTO users (first_name, last_name) VALUES (%s, %s)",
                        (first_name, last_name)
                    )
                    result = cursor.lastrowid
                    print(f"✅ Создан пользователь ID: {result}")
                
                cursor.close()
                return result
                
            except Error as e:
                print(f"❌ Ошибка БД при создании пользователя: {e}")
                return None
            except Exception as e:
                print(f"❌ Неизвестная ошибка: {e}")
                traceback.print_exc()
                return None
    
    def save_exercise_1(self, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 1"""
        return self._save_exercise("exercise_1_results", user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score)
    
    def save_exercise_2(self, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 2"""
        return self._save_exercise("exercise_2_results", user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score)
    
    def save_exercise_3(self, user_id, apples_count, speed, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 3"""
        return self._save_exercise("exercise_3_results", user_id, apples_count, speed, background, caught_apples, coefficient, total_score, is_exercise_3=True)
    
    def save_exercise_4(self, user_id, apples_count, time_sec, amplitude, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 4"""
        return self._save_exercise_4_5_7_9("exercise_4_results", user_id, apples_count, time_sec, amplitude, background, caught_apples, coefficient, total_score)
    
    def save_exercise_5(self, user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 5"""
        return self._save_exercise_4_5_7_9("exercise_5_results", user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score)
    
    def save_exercise_6(self, user_id, apples_count, time_sec, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 6"""
        return self._save_exercise_6("exercise_6_results", user_id, apples_count, time_sec, background, caught_apples, coefficient, total_score)
    
    def save_exercise_7(self, user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 7"""
        return self._save_exercise_4_5_7_9("exercise_7_results", user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score)
    
    def save_exercise_8(self, user_id, apples_count, time_sec, color_interval, speed, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 8"""
        return self._save_exercise_8("exercise_8_results", user_id, apples_count, time_sec, color_interval, speed, background, caught_apples, coefficient, total_score)
    
    def save_exercise_9(self, user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 9"""
        return self._save_exercise_4_5_7_9("exercise_9_results", user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score)
    
    def _save_exercise(self, table_name, user_id, apples_count, param2, background, caught_apples, coefficient, total_score, is_exercise_3=False):
        """Общий метод сохранения упражнений"""
        print(f" Сохранение в {table_name} для пользователя {user_id}")
        
        with self.lock:
            try:
                # Проверяем соединение
                if not self._ensure_connection():
                    print(" Нет соединения с БД")
                    return False
                
                cursor = self.connection.cursor()
                
                if is_exercise_3:
                    # Для упражнения 3
                    cursor.execute(f"""
                        INSERT INTO {table_name} 
                        (user_id, apples_count, speed, background, caught_apples, coefficient, total_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, apples_count, param2, background, caught_apples, coefficient, total_score))
                else:
                    # Для упражнений 1 и 2
                    cursor.execute(f"""
                        INSERT INTO {table_name} 
                        (user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, apples_count, param2, background, caught_apples, coefficient, total_score))
                
                self.connection.commit()
                cursor.close()
                print(f" Упражнение сохранено успешно")
                return True
                
            except Error as e:
                print(f" Ошибка сохранения: {e}")
                return False
            except Exception as e:
                print(f" Неизвестная ошибка при сохранении: {e}")
                traceback.print_exc()
                return False
    
    def _save_exercise_4_5_7_9(self, table_name, user_id, apples_count, time_sec, param3, background, caught_apples, coefficient, total_score):
        """Сохранение упражнений 4, 5, 7, 9 (с параметром amplitude/neck_range)"""
        print(f" Сохранение в {table_name} для пользователя {user_id}")
        
        with self.lock:
            try:
                if not self._ensure_connection():
                    print(" Нет соединения с БД")
                    return False
                
                cursor = self.connection.cursor()
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    (user_id, apples_count, time_sec, param3, background, caught_apples, coefficient, total_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, apples_count, time_sec, param3, background, caught_apples, coefficient, total_score))
                
                self.connection.commit()
                cursor.close()
                print(f" Упражнение сохранено успешно")
                return True
                
            except Error as e:
                print(f" Ошибка сохранения: {e}")
                return False
            except Exception as e:
                print(f" Неизвестная ошибка при сохранении: {e}")
                traceback.print_exc()
                return False
    
    def _save_exercise_6(self, table_name, user_id, apples_count, time_sec, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 6 (без дополнительного параметра)"""
        print(f" Сохранение в {table_name} для пользователя {user_id}")
        
        with self.lock:
            try:
                if not self._ensure_connection():
                    print(" Нет соединения с БД")
                    return False
                
                cursor = self.connection.cursor()
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    (user_id, apples_count, time_sec, background, caught_apples, coefficient, total_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, apples_count, time_sec, background, caught_apples, coefficient, total_score))
                
                self.connection.commit()
                cursor.close()
                print(f" Упражнение сохранено успешно")
                return True
                
            except Error as e:
                print(f" Ошибка сохранения: {e}")
                return False
            except Exception as e:
                print(f" Неизвестная ошибка при сохранении: {e}")
                traceback.print_exc()
                return False
    
    def _save_exercise_8(self, table_name, user_id, apples_count, time_sec, color_interval, speed, background, caught_apples, coefficient, total_score):
        """Сохранение упражнения 8 (с двумя дополнительными параметрами)"""
        print(f" Сохранение в {table_name} для пользователя {user_id}")
        
        with self.lock:
            try:
                if not self._ensure_connection():
                    print(" Нет соединения с БД")
                    return False
                
                cursor = self.connection.cursor()
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    (user_id, apples_count, time_sec, color_interval, speed, background, caught_apples, coefficient, total_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, apples_count, time_sec, color_interval, speed, background, caught_apples, coefficient, total_score))
                
                self.connection.commit()
                cursor.close()
                print(f" Упражнение сохранено успешно")
                return True
                
            except Error as e:
                print(f" Ошибка сохранения: {e}")
                return False
            except Exception as e:
                print(f" Неизвестная ошибка при сохранении: {e}")
                traceback.print_exc()
                return False
    
    def close(self):
        """Закрытие соединения"""
        with self.lock:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                self.is_connected = False
                print("✅ Соединение с БД закрыто")
    
    def get_exercise_history_by_user(self, user_id, limit=50):
        """Получение истории упражнений для конкретного пользователя"""
        print(f"🔄 Получение истории для пользователя ID: {user_id}")
        
        with self.lock:
            try:
                if not self._ensure_connection():
                    print("❌ Нет соединения с БД")
                    return []
                
                existing_tables = self._get_existing_table_names()
                query_parts = []
                params = []
                for table, alias, exercise_name, difficulty_expr in EXERCISE_HISTORY_QUERIES:
                    if table not in existing_tables:
                        continue
                    query_parts.append(f"""
                        SELECT '{exercise_name}' as exercise_type, {alias}.exercise_date,
                               CONCAT(u.first_name, ' ', u.last_name) as user_name,
                               {alias}.apples_count as total_apples, {alias}.caught_apples,
                               {difficulty_expr} as difficulty, {alias}.background,
                               {alias}.coefficient, {alias}.total_score
                        FROM {table} {alias}
                        JOIN users u ON {alias}.user_id = u.id
                        WHERE {alias}.user_id = %s
                    """)
                    params.append(user_id)

                if not query_parts:
                    print("⚠️ Нет таблиц с результатами упражнений")
                    return []

                query = " UNION ALL ".join(query_parts) + " ORDER BY exercise_date DESC LIMIT %s"
                params.append(limit)

                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(query, tuple(params))
                records = cursor.fetchall()
                cursor.close()
                print(f"✅ Получено записей: {len(records)}")
                return records
            except Error as e:
                print(f"❌ Ошибка: {e}")
                traceback.print_exc()
                return []
            except Exception as e:
                print(f"❌ Неизвестная ошибка: {e}")
                traceback.print_exc()
                return []
    
    def get_all_users(self):
        """Получение всех пользователей из БД"""
        print("🔄 Получение всех пользователей...")
        
        with self.lock:
            try:
                if not self._ensure_connection():
                    print("❌ Нет соединения с БД")
                    return []
                
                cursor = self.connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, first_name, last_name 
                    FROM users 
                    ORDER BY last_name, first_name
                """)
                users = cursor.fetchall()
                cursor.close()
                print(f"✅ Получено пользователей: {len(users)}")
                return users
            except Error as e:
                print(f"❌ Ошибка при получении пользователей: {e}")
                traceback.print_exc()
                return []
            except Exception as e:
                print(f"❌ Неизвестная ошибка при получении пользователей: {e}")
                traceback.print_exc()
                return []
    
    def get_exercise_sessions(self, user_id, exercise_id, limit=6):
        """Последние сессии одного упражнения (хронологический порядок)."""
        table = EXERCISE_TABLES.get(exercise_id)
        if not table:
            return []

        with self.lock:
            try:
                if not self._ensure_connection():
                    return []

                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(
                    f"""
                    SELECT apples_count, caught_apples, exercise_date,
                           coefficient, total_score
                    FROM {table}
                    WHERE user_id = %s
                    ORDER BY exercise_date DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cursor.fetchall()
                cursor.close()
                rows.reverse()
                return rows
            except Error as e:
                print(f"❌ Ошибка get_exercise_sessions: {e}")
                return []

    def save_doctor_baseline(self, user_id, exercise_id, params: dict):
        """Сохранить назначение врача для упражнения."""
        self._ensure_doctor_baseline_table()

        with self.lock:
            try:
                if not self._ensure_connection():
                    return False

                payload = json.dumps(params, ensure_ascii=False)
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO doctor_baseline (user_id, exercise_id, params_json)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        params_json = VALUES(params_json),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, exercise_id, payload),
                )
                self.connection.commit()
                cursor.close()
                return True
            except Error as e:
                print(f"❌ Ошибка save_doctor_baseline: {e}")
                return False

    def get_doctor_baseline(self, user_id, exercise_id):
        """Получить назначение врача или None."""
        self._ensure_doctor_baseline_table()

        with self.lock:
            try:
                if not self._ensure_connection():
                    return None

                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT params_json
                    FROM doctor_baseline
                    WHERE user_id = %s AND exercise_id = %s
                    """,
                    (user_id, exercise_id),
                )
                row = cursor.fetchone()
                cursor.close()
                if not row:
                    return None
                return json.loads(row["params_json"])
            except Error as e:
                print(f"❌ Ошибка get_doctor_baseline: {e}")
                return None

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