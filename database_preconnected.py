# database_preconnected.py
import json
import mysql.connector
from mysql.connector import Error
import threading
import traceback

from workspace import WorkspaceProfile

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
                host="127.0.0.1",
                port="3306",
                database="trainer",
                user="me",
                password="pass",
                autocommit=True,
                pool_size=1,
                connect_timeout=5
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
            else:
                self._ensure_exercise_1_columns()
                
        except Error as e:
            print(f"⚠️ Ошибка при проверке таблиц: {e}")

    def _ensure_exercise_1_columns(self):
        """Миграция: session_duration_sec, exit_reason в exercise_1_results."""
        if not self.is_connected:
            return
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW COLUMNS FROM exercise_1_results LIKE 'session_duration_sec'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE exercise_1_results ADD COLUMN session_duration_sec INT NULL"
                )
                print("✅ Добавлен столбец session_duration_sec")
            cursor.execute("SHOW COLUMNS FROM exercise_1_results LIKE 'exit_reason'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE exercise_1_results ADD COLUMN exit_reason VARCHAR(32) NULL"
                )
                print("✅ Добавлен столбец exit_reason")
            self.connection.commit()
            cursor.close()
        except Error as e:
            print(f"⚠️ Миграция exercise_1_results: {e}")
    
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
    
    def save_exercise_1(self, user_id, apples_count, seconds_per_apple, background, caught_apples,
                        coefficient, total_score, session_duration_sec=None, exit_reason=None):
        """Сохранение упражнения 1"""
        return self._save_exercise(
            "exercise_1_results", user_id, apples_count, seconds_per_apple, background,
            caught_apples, coefficient, total_score,
            session_duration_sec=session_duration_sec, exit_reason=exit_reason,
        )
    
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
    
    def _save_exercise(self, table_name, user_id, apples_count, param2, background, caught_apples,
                       coefficient, total_score, is_exercise_3=False,
                       session_duration_sec=None, exit_reason=None):
        """Общий метод сохранения упражнений"""
        print(f" Сохранение в {table_name} для пользователя {user_id}")
        
        with self.lock:
            try:
                # Проверяем соединение
                if not self._ensure_connection():
                    print(" Нет соединения с БД")
                    return False

                if table_name == "exercise_1_results":
                    self._ensure_exercise_1_columns()
                
                cursor = self.connection.cursor()
                
                if is_exercise_3:
                    # Для упражнения 3
                    cursor.execute(f"""
                        INSERT INTO {table_name} 
                        (user_id, apples_count, speed, background, caught_apples, coefficient, total_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, apples_count, param2, background, caught_apples, coefficient, total_score))
                elif table_name == "exercise_1_results" and (
                    session_duration_sec is not None or exit_reason is not None
                ):
                    cursor.execute(f"""
                        INSERT INTO {table_name}
                        (user_id, apples_count, seconds_per_apple, background, caught_apples,
                         coefficient, total_score, session_duration_sec, exit_reason)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_id, apples_count, param2, background, caught_apples,
                        coefficient, total_score, session_duration_sec, exit_reason,
                    ))
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
                
                cursor = self.connection.cursor(dictionary=True)
                query = """
                    SELECT 'Упражнение 1' as exercise_type, e1.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e1.apples_count as total_apples, e1.caught_apples, CONCAT(e1.seconds_per_apple, ' сек') as difficulty, e1.background, e1.coefficient, e1.total_score
                    FROM exercise_1_results e1 JOIN users u ON e1.user_id = u.id WHERE e1.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 2' as exercise_type, e2.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e2.apples_count as total_apples, e2.caught_apples, CONCAT(e2.seconds_per_apple, ' сек') as difficulty, e2.background, e2.coefficient, e2.total_score
                    FROM exercise_2_results e2 JOIN users u ON e2.user_id = u.id WHERE e2.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 3' as exercise_type, e3.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e3.apples_count as total_apples, e3.caught_apples, e3.speed as difficulty, e3.background, e3.coefficient, e3.total_score
                    FROM exercise_3_results e3 JOIN users u ON e3.user_id = u.id WHERE e3.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 4' as exercise_type, e4.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e4.apples_count as total_apples, e4.caught_apples, e4.param3 as difficulty, e4.background, e4.coefficient, e4.total_score
                    FROM exercise_4_results e4 JOIN users u ON e4.user_id = u.id WHERE e4.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 5' as exercise_type, e5.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e5.apples_count as total_apples, e5.caught_apples, e5.param3 as difficulty, e5.background, e5.coefficient, e5.total_score
                    FROM exercise_5_results e5 JOIN users u ON e5.user_id = u.id WHERE e5.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 6' as exercise_type, e6.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e6.apples_count as total_apples, e6.caught_apples, CONCAT(e6.time_sec, ' сек') as difficulty, e6.background, e6.coefficient, e6.total_score
                    FROM exercise_6_results e6 JOIN users u ON e6.user_id = u.id WHERE e6.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 7' as exercise_type, e7.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e7.apples_count as total_apples, e7.caught_apples, e7.param3 as difficulty, e7.background, e7.coefficient, e7.total_score
                    FROM exercise_7_results e7 JOIN users u ON e7.user_id = u.id WHERE e7.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 8' as exercise_type, e8.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e8.apples_count as total_apples, e8.caught_apples, CONCAT(e8.speed, ' / ', e8.color_interval, 'с') as difficulty, e8.background, e8.coefficient, e8.total_score
                    FROM exercise_8_results e8 JOIN users u ON e8.user_id = u.id WHERE e8.user_id = %s
                    UNION ALL
                    SELECT 'Упражнение 9' as exercise_type, e9.exercise_date, CONCAT(u.first_name, ' ', u.last_name) as user_name, e9.apples_count as total_apples, e9.caught_apples, e9.param3 as difficulty, e9.background, e9.coefficient, e9.total_score
                    FROM exercise_9_results e9 JOIN users u ON e9.user_id = u.id WHERE e9.user_id = %s
                    ORDER BY exercise_date DESC LIMIT %s
                """
                cursor.execute(query, (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, limit))
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
    
    def get_exercise_1_results_raw(self, user_id, limit=50):
        """Сырые результаты упражнения 1 (новые первыми)."""
        print(f"🔄 get_exercise_1_results_raw user_id={user_id} limit={limit}")
        with self.lock:
            try:
                if not self._ensure_connection():
                    return []
                self._ensure_exercise_1_columns()
                cursor = self.connection.cursor(dictionary=True)
                try:
                    cursor.execute("""
                        SELECT id, apples_count, seconds_per_apple, background, caught_apples,
                               exercise_date, coefficient, total_score,
                               session_duration_sec, exit_reason
                        FROM exercise_1_results
                        WHERE user_id = %s
                        ORDER BY exercise_date DESC
                        LIMIT %s
                    """, (user_id, limit))
                except Error:
                    cursor.execute("""
                        SELECT id, apples_count, seconds_per_apple, background, caught_apples,
                               exercise_date, coefficient, total_score
                        FROM exercise_1_results
                        WHERE user_id = %s
                        ORDER BY exercise_date DESC
                        LIMIT %s
                    """, (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()
                print(f"✅ exercise_1_results: {len(rows)} записей")
                return rows
            except Error as e:
                print(f"❌ get_exercise_1_results_raw: {e}")
                return []

    def has_user_calibration(self, user_id):
        """Есть ли сохранённая калибровка пользователя."""
        if user_id is None:
            return False
        with self.lock:
            try:
                if not self._ensure_connection():
                    return False
                cursor = self.connection.cursor()
                cursor.execute("SHOW TABLES LIKE 'user_calibration'")
                if not cursor.fetchone():
                    cursor.close()
                    # Agent 1 ещё не создал таблицу — не блокируем рекомендации
                    return True
                cursor.execute(
                    "SELECT 1 FROM user_calibration WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
                found = cursor.fetchone() is not None
                cursor.close()
                return found
            except Error:
                return False

    def delete_user(self, user_id):
        with self.lock:
            try:
                if not self._ensure_connection():
                    return False
                
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM user_calibration WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                self.connection.commit()
                cursor.close()
                return True
            except Exception as e:
                print(e)
                return False

    def _ensure_calibration_table(self):
        """CREATE TABLE IF NOT EXISTS user_calibration (Agent 1)."""
        if not self._ensure_connection():
            return False
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_calibration (
                    user_id INT PRIMARY KEY,
                    x_min INT NOT NULL,
                    x_max INT NOT NULL,
                    y_min INT NOT NULL,
                    y_max INT NOT NULL,
                    frame_w INT NOT NULL,
                    frame_h INT NOT NULL,
                    touch_points_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.close()
            return True
        except Error as e:
            print(f"❌ Ошибка создания user_calibration: {e}")
            return False

    def save_user_calibration(self, user_id, profile, touch_points=None):
        """Сохранение или обновление профиля рабочей зоны пользователя."""
        if profile is None or user_id is None:
            return False

        with self.lock:
            try:
                if not self._ensure_calibration_table():
                    return False

                touch_json = None
                if touch_points:
                    touch_json = json.dumps([[int(x), int(y)] for x, y in touch_points])

                cursor = self.connection.cursor()
                cursor.execute("""
                    INSERT INTO user_calibration
                        (user_id, x_min, x_max, y_min, y_max, frame_w, frame_h, touch_points_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        x_min = VALUES(x_min),
                        x_max = VALUES(x_max),
                        y_min = VALUES(y_min),
                        y_max = VALUES(y_max),
                        frame_w = VALUES(frame_w),
                        frame_h = VALUES(frame_h),
                        touch_points_json = VALUES(touch_points_json)
                """, (
                    user_id,
                    profile.x_min,
                    profile.x_max,
                    profile.y_min,
                    profile.y_max,
                    profile.frame_w,
                    profile.frame_h,
                    touch_json,
                ))
                self.connection.commit()
                cursor.close()
                print(f"✅ Калибровка сохранена для user_id={user_id}")
                return True
            except Error as e:
                print(f"❌ Ошибка сохранения калибровки: {e}")
                return False
            except Exception as e:
                print(f"❌ Неизвестная ошибка сохранения калибровки: {e}")
                traceback.print_exc()
                return False

    def get_user_calibration(self, user_id):
        """Загрузка WorkspaceProfile для пользователя или None."""
        if user_id is None:
            return None

        with self.lock:
            try:
                if not self._ensure_calibration_table():
                    return None

                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT x_min, x_max, y_min, y_max, frame_w, frame_h
                    FROM user_calibration
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                cursor.close()

                if not row:
                    return None

                return WorkspaceProfile(
                    int(row["x_min"]),
                    int(row["x_max"]),
                    int(row["y_min"]),
                    int(row["y_max"]),
                    int(row["frame_w"]),
                    int(row["frame_h"]),
                )
            except Error as e:
                print(f"❌ Ошибка загрузки калибровки: {e}")
                return None
            except Exception as e:
                print(f"❌ Неизвестная ошибка загрузки калибровки: {e}")
                traceback.print_exc()
                return None