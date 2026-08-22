"""Локальное хранилище на SQLite.

База не требует отдельного сервера: модуль sqlite3 входит в Python.
После установки приложения рабочая копия создаётся из data/trainer.seed.db
(уже есть тестовый пациент). Существующий файл не перезаписывается.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app_paths import project_root, user_data_dir

APP_NAME = "RehabTrainer"
DB_FILENAME = "trainer.db"
SEED_FILENAME = "trainer.seed.db"
DEMO_USER = {"first_name": "Тест", "last_name": "Пациент"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (first_name, last_name)
);

CREATE TABLE IF NOT EXISTS exercise_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    apples_count INTEGER NOT NULL,
    caught_apples INTEGER NOT NULL,
    coefficient REAL NOT NULL,
    total_score REAL NOT NULL,
    background TEXT,
    difficulty TEXT,
    params_json TEXT NOT NULL DEFAULT '{}',
    exercise_date TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS doctor_baseline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    params_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (user_id, exercise_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_results_user_exercise_date
    ON exercise_results (user_id, exercise_id, exercise_date);
"""


def seed_db_path() -> Path:
    return project_root() / "data" / SEED_FILENAME


def runtime_db_path() -> Path:
    return user_data_dir() / DB_FILENAME


def avatars_dir() -> Path:
    folder = user_data_dir() / "avatars"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def avatar_file(user_id: int) -> Path:
    return avatars_dir() / f"user_{user_id}.png"


def save_avatar_pixmap(user_id: int, pixmap) -> Path:
    """Сохраняет квадратный PNG 256×256 из QPixmap."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QPixmap

    size = 256
    if not isinstance(pixmap, QPixmap) or pixmap.isNull():
        raise ValueError("empty pixmap")
    scaled = pixmap.scaled(
        size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)
    path = avatar_file(user_id)
    cropped.save(str(path), "PNG")
    return path


def delete_avatar_file(user_id: int) -> None:
    path = avatar_file(user_id)
    if path.exists():
        path.unlink()


def _parse_dt(value: Any) -> Any:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return value


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    data = {col[0]: row[i] for i, col in enumerate(cursor.description)}
    if "exercise_date" in data:
        data["exercise_date"] = _parse_dt(data["exercise_date"])
    if "updated_at" in data:
        data["updated_at"] = _parse_dt(data["updated_at"])
    if "created_at" in data:
        data["created_at"] = _parse_dt(data["created_at"])
    return data


def _apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)


def _seed_demo_user(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO users (first_name, last_name)
        VALUES (:first_name, :last_name)
        """,
        DEMO_USER,
    )


def write_seed_database(path: Optional[Path] = None) -> Path:
    """Создаёт заводскую БД с таблицами и тестовым пациентом."""
    target = path or seed_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    conn = sqlite3.connect(str(target))
    try:
        _apply_schema(conn)
        _seed_demo_user(conn)
        conn.commit()
    finally:
        conn.close()
    return target


def ensure_runtime_database() -> Path:
    """Копирует seed в рабочий файл, если рабочей БД ещё нет."""
    target = runtime_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target

    seed = seed_db_path()
    if seed.exists():
        shutil.copy2(seed, target)
        return target

    write_seed_database(target)
    return target


class Database:
    """Тот же интерфейс, что был у DatabasePreconnected."""

    def __init__(self, db_path: Optional[Path] = None):
        self.lock = threading.Lock()
        self.connection: Optional[sqlite3.Connection] = None
        self.is_connected = False
        self.db_path = Path(db_path) if db_path else ensure_runtime_database()
        self._initial_connect()

    def _initial_connect(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(
                str(self.db_path),
                timeout=5,
                check_same_thread=False,
            )
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA journal_mode = WAL")
            _apply_schema(self.connection)
            self.connection.commit()
            self.is_connected = True
            print(f"✅ Локальная БД: {self.db_path}")
        except sqlite3.Error as e:
            print(f"❌ Ошибка открытия SQLite: {e}")
            traceback.print_exc()
            self.connection = None
            self.is_connected = False

    def _ensure_connection(self) -> bool:
        if self.is_connected and self.connection is not None:
            try:
                self.connection.execute("SELECT 1")
                return True
            except sqlite3.Error:
                self.is_connected = False
        self._initial_connect()
        return self.is_connected

    def connect(self) -> bool:
        return self._ensure_connection()

    def close(self) -> None:
        with self.lock:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
                self.is_connected = False
                print("✅ Соединение с БД закрыто")

    def get_or_create_user(self, first_name: str, last_name: str) -> Optional[int]:
        print(f"🔄 Создание пользователя: {first_name} {last_name}")
        with self.lock:
            if not self._ensure_connection():
                return None
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT id FROM users WHERE first_name = ? AND last_name = ?",
                    (first_name, last_name),
                )
                row = cursor.fetchone()
                if row:
                    print(f"✅ Найден пользователь ID: {row[0]}")
                    return int(row[0])
                cursor.execute(
                    "INSERT INTO users (first_name, last_name) VALUES (?, ?)",
                    (first_name, last_name),
                )
                self.connection.commit()
                user_id = int(cursor.lastrowid)
                print(f"✅ Создан пользователь ID: {user_id}")
                return user_id
            except sqlite3.Error as e:
                print(f"❌ Ошибка БД при создании пользователя: {e}")
                return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self.lock:
            if not self._ensure_connection():
                return []
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT id, first_name, last_name
                    FROM users
                    ORDER BY last_name, first_name
                    """
                )
                users = [_row_to_dict(cursor, row) for row in cursor.fetchall()]
                print(f"✅ Получено пользователей: {len(users)}")
                return users
            except sqlite3.Error as e:
                print(f"❌ Ошибка при получении пользователей: {e}")
                return []

    def delete_user(self, user_id: int) -> bool:
        with self.lock:
            if not self._ensure_connection():
                return False
            try:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                self.connection.commit()
                deleted = cursor.rowcount > 0
            except sqlite3.Error as e:
                print(e)
                return False
        if deleted:
            delete_avatar_file(user_id)
        return deleted

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            if not self._ensure_connection() or not user_id:
                return None
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT id, first_name, last_name FROM users WHERE id = ?",
                    (user_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return _row_to_dict(cursor, row)
            except sqlite3.Error as e:
                print(f"❌ Ошибка get_user: {e}")
                return None

    def update_user(self, user_id: int, first_name: str, last_name: str) -> bool:
        with self.lock:
            if not self._ensure_connection():
                return False
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT id FROM users
                    WHERE first_name = ? AND last_name = ? AND id != ?
                    """,
                    (first_name, last_name, user_id),
                )
                if cursor.fetchone():
                    return False
                cursor.execute(
                    "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?",
                    (first_name, last_name, user_id),
                )
                self.connection.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                print(f"❌ Ошибка update_user: {e}")
                return False

    def save_exercise_1(
        self, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            1,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            f"{seconds_per_apple} сек",
            {"seconds_per_apple": seconds_per_apple},
        )

    def save_exercise_2(
        self, user_id, apples_count, seconds_per_apple, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            2,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            f"{seconds_per_apple} сек",
            {"seconds_per_apple": seconds_per_apple},
        )

    def save_exercise_3(
        self, user_id, apples_count, speed, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            3,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            str(speed),
            {"speed": speed},
        )

    def save_exercise_4(
        self, user_id, apples_count, time_sec, amplitude, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            4,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            str(amplitude),
            {"time_sec": time_sec, "param3": amplitude},
        )

    def save_exercise_5(
        self, user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            5,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            str(neck_range),
            {"time_sec": time_sec, "param3": neck_range},
        )

    def save_exercise_6(
        self, user_id, apples_count, time_sec, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            6,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            f"{time_sec} сек",
            {"time_sec": time_sec},
        )

    def save_exercise_7(
        self, user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            7,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            str(neck_range),
            {"time_sec": time_sec, "param3": neck_range},
        )

    def save_exercise_8(
        self,
        user_id,
        apples_count,
        time_sec,
        color_interval,
        speed,
        background,
        caught_apples,
        coefficient,
        total_score,
    ) -> bool:
        return self._save_result(
            user_id,
            8,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            f"{speed} / {color_interval}с",
            {"time_sec": time_sec, "color_interval": color_interval, "speed": speed},
        )

    def save_exercise_9(
        self, user_id, apples_count, time_sec, neck_range, background, caught_apples, coefficient, total_score
    ) -> bool:
        return self._save_result(
            user_id,
            9,
            apples_count,
            caught_apples,
            coefficient,
            total_score,
            background,
            str(neck_range),
            {"time_sec": time_sec, "param3": neck_range},
        )

    def _save_result(
        self,
        user_id,
        exercise_id: int,
        apples_count,
        caught_apples,
        coefficient,
        total_score,
        background,
        difficulty: str,
        params: Dict[str, Any],
    ) -> bool:
        print(f" Сохранение упражнения {exercise_id} для пользователя {user_id}")
        with self.lock:
            if not self._ensure_connection() or user_id is None:
                print(" Нет соединения с БД")
                return False
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO exercise_results (
                        user_id, exercise_id, apples_count, caught_apples,
                        coefficient, total_score, background, difficulty, params_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        exercise_id,
                        apples_count,
                        caught_apples,
                        coefficient,
                        total_score,
                        background,
                        difficulty,
                        json.dumps(params, ensure_ascii=False),
                    ),
                )
                self.connection.commit()
                print(" Упражнение сохранено успешно")
                return True
            except sqlite3.Error as e:
                print(f" Ошибка сохранения: {e}")
                return False
            except Exception as e:
                print(f" Неизвестная ошибка при сохранении: {e}")
                traceback.print_exc()
                return False

    def get_exercise_history_by_user(self, user_id, limit: int = 50) -> List[Dict[str, Any]]:
        print(f"🔄 Получение истории для пользователя ID: {user_id}")
        with self.lock:
            if not self._ensure_connection():
                return []
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT
                        r.exercise_id,
                        CASE r.exercise_id
                            WHEN 1 THEN 'Упражнение 1'
                            WHEN 2 THEN 'Упражнение 2'
                            WHEN 3 THEN 'Упражнение 3'
                            WHEN 4 THEN 'Упражнение 4'
                            WHEN 5 THEN 'Упражнение 5'
                            WHEN 6 THEN 'Упражнение 6'
                            WHEN 7 THEN 'Упражнение 7'
                            WHEN 8 THEN 'Упражнение 8'
                            WHEN 9 THEN 'Упражнение 9'
                            ELSE 'Упражнение'
                        END AS exercise_type,
                        r.exercise_date,
                        (u.first_name || ' ' || u.last_name) AS user_name,
                        r.apples_count AS total_apples,
                        r.caught_apples,
                        r.difficulty,
                        r.background,
                        r.coefficient,
                        r.total_score
                    FROM exercise_results r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.user_id = ?
                    ORDER BY r.exercise_date DESC, r.id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                )
                records = [_row_to_dict(cursor, row) for row in cursor.fetchall()]
                print(f"✅ Получено записей: {len(records)}")
                return records
            except sqlite3.Error as e:
                print(f"❌ Ошибка: {e}")
                traceback.print_exc()
                return []

    def get_exercise_sessions(self, user_id, exercise_id, limit: int = 6) -> List[Dict[str, Any]]:
        with self.lock:
            if not self._ensure_connection():
                return []
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT apples_count, caught_apples, exercise_date,
                           coefficient, total_score
                    FROM exercise_results
                    WHERE user_id = ? AND exercise_id = ?
                    ORDER BY exercise_date DESC, id DESC
                    LIMIT ?
                    """,
                    (user_id, exercise_id, limit),
                )
                rows = [_row_to_dict(cursor, row) for row in cursor.fetchall()]
                rows.reverse()
                return rows
            except sqlite3.Error as e:
                print(f"❌ Ошибка get_exercise_sessions: {e}")
                return []

    def save_doctor_baseline(self, user_id, exercise_id, params: dict) -> bool:
        with self.lock:
            if not self._ensure_connection():
                return False
            try:
                payload = json.dumps(params, ensure_ascii=False)
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO doctor_baseline (user_id, exercise_id, params_json, updated_at)
                    VALUES (?, ?, ?, datetime('now', 'localtime'))
                    ON CONFLICT(user_id, exercise_id) DO UPDATE SET
                        params_json = excluded.params_json,
                        updated_at = datetime('now', 'localtime')
                    """,
                    (user_id, exercise_id, payload),
                )
                self.connection.commit()
                return True
            except sqlite3.Error as e:
                print(f"❌ Ошибка save_doctor_baseline: {e}")
                return False

    def get_doctor_baseline(self, user_id, exercise_id):
        with self.lock:
            if not self._ensure_connection():
                return None
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    SELECT params_json
                    FROM doctor_baseline
                    WHERE user_id = ? AND exercise_id = ?
                    """,
                    (user_id, exercise_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return json.loads(row[0])
            except sqlite3.Error as e:
                print(f"❌ Ошибка get_doctor_baseline: {e}")
                return None


# Совместимость со старым именем класса
DatabasePreconnected = Database


if __name__ == "__main__":
    path = write_seed_database()
    print(f"Заводская БД записана: {path}")
