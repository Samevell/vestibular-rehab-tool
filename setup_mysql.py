#!/usr/bin/env python3
"""
Настройка MySQL для тренажёра:
  - создаёт базу данных (если нет)
  - создаёт все нужные таблицы
  - добавляет тестового пациента
  - сохраняет db_config.json для приложения

Запуск:
  python setup_mysql.py
  python setup_mysql.py --yes
  python setup_mysql.py --host 127.0.0.1 --user root --password secret
"""
from __future__ import annotations

import argparse
import getpass
import sys
from typing import Dict, List, Optional, Tuple

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Установите зависимость: pip install mysql-connector-python")
    sys.exit(1)

from db_config import DEFAULT_CONFIG, load_db_config, save_db_config

DEFAULT_PATIENT = {
    "first_name": "Тест",
    "last_name": "Пациент",
}

TABLE_DEFINITIONS: List[Tuple[str, str]] = [
    (
        "users",
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user (first_name, last_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "exercise_1_results",
        """
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
        """,
    ),
    (
        "exercise_2_results",
        """
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
        """,
    ),
    (
        "exercise_3_results",
        """
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
        """,
    ),
    (
        "doctor_baseline",
        """
        CREATE TABLE IF NOT EXISTS doctor_baseline (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            exercise_id INT NOT NULL,
            params_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_exercise (user_id, exercise_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ),
    (
        "exercise_4_results",
        """
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
        """,
    ),
    (
        "exercise_5_results",
        """
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
        """,
    ),
    (
        "exercise_6_results",
        """
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
        """,
    ),
    (
        "exercise_7_results",
        """
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
        """,
    ),
    (
        "exercise_8_results",
        """
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
        """,
    ),
    (
        "exercise_9_results",
        """
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
        """,
    ),
]


def prompt_config(args: argparse.Namespace) -> Dict[str, object]:
    current = load_db_config()

    def ask(label: str, key: str, *, secret: bool = False) -> str:
        default = str(current.get(key, DEFAULT_CONFIG[key]))
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            return str(cli_value)
        if args.yes:
            return default
        prompt = f"{label} [{default}]: "
        if secret:
            value = getpass.getpass(prompt)
            return value if value else default
        value = input(prompt).strip()
        return value if value else default

    return {
        "host": ask("Хост MySQL", "host"),
        "port": int(ask("Порт", "port")),
        "database": ask("Имя базы данных", "database"),
        "user": ask("Пользователь MySQL", "user"),
        "password": ask("Пароль MySQL", "password", secret=True),
    }


def prompt_patient(args: argparse.Namespace) -> Optional[Dict[str, str]]:
    if args.skip_patient:
        return None

    first_name = args.patient_first
    last_name = args.patient_last
    if first_name is not None and last_name is not None:
        return {"first_name": first_name, "last_name": last_name}
    if args.yes:
        return DEFAULT_PATIENT.copy()

    choice = input("\nСоздать тестового пациента? [Y/n]: ").strip().lower()
    if choice in ("n", "no", "нет"):
        return None

    first_default = DEFAULT_PATIENT["first_name"]
    last_default = DEFAULT_PATIENT["last_name"]
    first_name = input(f"Имя пациента [{first_default}]: ").strip() or first_default
    last_name = input(f"Фамилия пациента [{last_default}]: ").strip() or last_default
    return {"first_name": first_name, "last_name": last_name}


def connect_server(config: Dict[str, object]):
    return mysql.connector.connect(
        host=str(config["host"]),
        port=int(config["port"]),
        user=str(config["user"]),
        password=str(config["password"]),
        connection_timeout=10,
    )


def connect_database(config: Dict[str, object]):
    return mysql.connector.connect(
        host=str(config["host"]),
        port=int(config["port"]),
        user=str(config["user"]),
        password=str(config["password"]),
        database=str(config["database"]),
        connection_timeout=10,
    )


def ensure_database(config: Dict[str, object]) -> None:
    db_name = str(config["database"])
    print(f"\n1/4 Подключение к MySQL ({config['host']}:{config['port']})...")
    conn = connect_server(config)
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        print(f"   База данных '{db_name}' готова.")
    finally:
        cursor.close()
        conn.close()


def create_tables(config: Dict[str, object]) -> List[str]:
    print(f"\n2/4 Создание таблиц в '{config['database']}'...")
    conn = connect_database(config)
    cursor = conn.cursor()
    created: List[str] = []
    try:
        for table_name, ddl in TABLE_DEFINITIONS:
            cursor.execute(ddl)
            created.append(table_name)
            print(f"   OK  {table_name}")
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return created


def verify_tables(config: Dict[str, object]) -> List[str]:
    print("\n3/4 Проверка таблиц...")
    conn = connect_database(config)
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES")
        tables = sorted(row[0] for row in cursor.fetchall())
        print(f"   Таблиц в базе: {len(tables)}")
        for name in tables:
            print(f"   - {name}")
        return tables
    finally:
        cursor.close()
        conn.close()


def ensure_demo_patient(config: Dict[str, object], patient: Dict[str, str]) -> int:
    first_name = patient["first_name"]
    last_name = patient["last_name"]
    print(f"\n4/4 Тестовый пациент: {first_name} {last_name}...")

    conn = connect_database(config)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id FROM users WHERE first_name = %s AND last_name = %s",
            (first_name, last_name),
        )
        row = cursor.fetchone()
        if row:
            user_id = row["id"]
            print(f"   Уже существует (id={user_id})")
            return user_id

        cursor.execute(
            "INSERT INTO users (first_name, last_name) VALUES (%s, %s)",
            (first_name, last_name),
        )
        conn.commit()
        user_id = cursor.lastrowid
        print(f"   Создан (id={user_id})")
        return user_id
    finally:
        cursor.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Настройка MySQL для тренажёра")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--database")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="использовать значения по умолчанию / db_config.json без вопросов",
    )
    parser.add_argument("--patient-first", help="имя тестового пациента")
    parser.add_argument("--patient-last", help="фамилия тестового пациента")
    parser.add_argument(
        "--skip-patient",
        action="store_true",
        help="не создавать тестового пациента",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 50)
    print("Настройка MySQL для тренажёра")
    print("=" * 50)

    config = prompt_config(args)
    patient = prompt_patient(args)

    try:
        ensure_database(config)
        create_tables(config)
        verify_tables(config)
        if patient:
            ensure_demo_patient(config, patient)
        else:
            print("\n4/4 Тестовый пациент пропущен.")
    except Error as exc:
        print(f"\nОшибка MySQL: {exc}")
        print("\nПроверьте:")
        print("  - запущен ли MySQL Server")
        print("  - верны ли логин и пароль")
        print("  - есть ли права на CREATE DATABASE / CREATE TABLE")
        return 1

    save_db_config(config)
    print("\nГотово.")
    print(f"Настройки сохранены в db_config.json")
    print("Запуск приложения: python run_app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
