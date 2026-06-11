#!/usr/bin/env python3
"""
Проверка, установка и запуск MySQL Server.

Скрипт безопасен при уже установленном MySQL: ничего не переустанавливает,
только проверяет порт и при необходимости запускает службу.

Запуск:
  python install_mysql.py
  python install_mysql.py --yes
  python install_mysql.py --install
  python install_mysql.py --start-only
  python install_mysql.py --yes --setup
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence

MYSQL_PORT = 3306

WINDOWS_SERVICE_NAMES = ("MySQL80", "MySQL", "MySQL57", "MariaDB")
LINUX_SERVICE_NAMES = ("mysql", "mysqld", "mariadb")
MAC_SERVICE_NAMES = ("mysql", "mariadb")


def is_admin() -> bool:
    system = platform.system()
    if system == "Windows":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return getattr(os, "geteuid", lambda: 1)() == 0


def port_is_open(host: str = "127.0.0.1", port: int = MYSQL_PORT, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def try_mysql_connect() -> bool:
    try:
        import mysql.connector
        from db_config import mysql_connect_kwargs

        conn = mysql.connector.connect(**mysql_connect_kwargs(), connection_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


def mysql_is_running() -> bool:
    return port_is_open() or try_mysql_connect()


def run_command(cmd: Sequence[str], *, check: bool = False) -> subprocess.CompletedProcess:
    print(f"   > {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def windows_service_status(name: str) -> Optional[str]:
    result = subprocess.run(
        ["sc", "query", name],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "STATE" in line:
            return line.strip()
    return "FOUND"


def find_windows_mysql_services() -> List[str]:
    found = []
    for name in WINDOWS_SERVICE_NAMES:
        if windows_service_status(name):
            found.append(name)
    return found


def start_windows_service(name: str) -> bool:
    result = run_command(["net", "start", name])
    return result.returncode == 0


def start_linux_service(name: str, *, use_sudo: bool) -> bool:
    cmd = (["sudo"] if use_sudo else []) + ["systemctl", "start", name]
    return run_command(cmd).returncode == 0


def start_mac_service(name: str) -> bool:
    if shutil.which("brew"):
        return run_command(["brew", "services", "start", name]).returncode == 0
    return False


def wait_for_mysql(seconds: int = 30) -> bool:
    print(f"   Ожидание MySQL (до {seconds} с)...")
    for _ in range(seconds):
        if mysql_is_running():
            return True
        time.sleep(1)
    return False


def start_mysql_service() -> bool:
    system = platform.system()

    if system == "Windows":
        services = find_windows_mysql_services()
        if not services:
            print("   Служба MySQL не найдена (MySQL80 / MySQL / MariaDB).")
            return False
        for name in services:
            status = windows_service_status(name) or ""
            if "RUNNING" in status:
                print(f"   Служба {name} уже запущена.")
                return True
            print(f"   Запуск службы {name}...")
            if start_windows_service(name):
                return wait_for_mysql()
        return False

    if system == "Linux":
        use_sudo = not is_admin()
        for name in LINUX_SERVICE_NAMES:
            if run_command((["sudo"] if use_sudo else []) + ["systemctl", "status", name]).returncode == 0:
                print(f"   Запуск службы {name}...")
                if start_linux_service(name, use_sudo=use_sudo):
                    return wait_for_mysql()
        print("   Служба mysql/mariadb не найдена.")
        return False

    if system == "Darwin":
        for name in MAC_SERVICE_NAMES:
            if start_mac_service(name):
                return wait_for_mysql()
        print("   Не удалось запустить mysql через brew services.")
        return False

    print(f"   ОС '{system}' не поддерживается автоматически.")
    return False


def install_mysql_windows() -> bool:
    if shutil.which("winget"):
        print("   Установка через winget (Oracle.MySQL)...")
        result = run_command(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "Oracle.MySQL",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
        if result.returncode == 0:
            return wait_for_mysql(60)
        print("   winget не смог установить MySQL.")

    if shutil.which("choco"):
        print("   Установка через Chocolatey (mysql)...")
        result = run_command(["choco", "install", "mysql", "-y"])
        if result.returncode == 0:
            return wait_for_mysql(60)

    print_manual_windows_instructions()
    return False


def install_mysql_linux() -> bool:
    if shutil.which("apt-get"):
        print("   Установка через apt (mysql-server)...")
        if run_command(["sudo", "apt-get", "update", "-y"]).returncode != 0:
            return False
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
        result = subprocess.run(
            ["sudo", "apt-get", "install", "-y", "mysql-server"],
            env=env,
        )
        print(f"   > sudo apt-get install -y mysql-server")
        if result.returncode != 0:
            return False
        run_command(["sudo", "systemctl", "enable", "--now", "mysql"])
        return wait_for_mysql(30)

    if shutil.which("dnf"):
        print("   Установка через dnf (mysql-server)...")
        if run_command(["sudo", "dnf", "install", "-y", "mysql-server"]).returncode != 0:
            return False
        run_command(["sudo", "systemctl", "enable", "--now", "mysqld"])
        return wait_for_mysql(30)

    print("   Поддерживаются apt и dnf. Установите mysql-server вручную.")
    return False


def install_mysql_macos() -> bool:
    if not shutil.which("brew"):
        print("   Установите Homebrew: https://brew.sh")
        return False
    print("   Установка через brew (mysql)...")
    if run_command(["brew", "install", "mysql"]).returncode != 0:
        return False
    run_command(["brew", "services", "start", "mysql"])
    return wait_for_mysql(30)


def install_mysql() -> bool:
    system = platform.system()
    if system == "Windows":
        return install_mysql_windows()
    if system == "Linux":
        return install_mysql_linux()
    if system == "Darwin":
        return install_mysql_macos()
    return False


def print_manual_windows_instructions() -> None:
    print(
        """
   Ручная установка на Windows:
   1. Скачайте MySQL Installer: https://dev.mysql.com/downloads/installer/
   2. Выберите MySQL Server, задайте root-пароль (по умолчанию в проекте: pass)
   3. После установки запустите снова: python install_mysql.py
"""
    )


def run_setup_mysql(extra_args: List[str]) -> int:
    script = Path(__file__).resolve().parent / "setup_mysql.py"
    cmd = [sys.executable, str(script), *extra_args]
    print("\nЗапуск настройки базы (setup_mysql.py)...")
    return subprocess.call(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Установка и запуск MySQL Server")
    parser.add_argument(
        "--install",
        action="store_true",
        help="попытаться установить MySQL, если не найден",
    )
    parser.add_argument(
        "--start-only",
        action="store_true",
        help="только запустить службу, не устанавливать",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="после запуска MySQL выполнить setup_mysql.py",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="передать --yes в setup_mysql.py",
    )
    return parser.parse_args()


def finish_success(args: argparse.Namespace) -> int:
    if args.setup:
        setup_args = ["--yes"] if args.yes else []
        return run_setup_mysql(setup_args)
    print("Дальше: python setup_mysql.py")
    return 0


def main() -> int:
    args = parse_args()

    print("=" * 50)
    print("MySQL: проверка / установка / запуск")
    print(f"ОС: {platform.system()} {platform.release()}")
    print("=" * 50)

    if mysql_is_running():
        print(f"\nMySQL уже доступен на порту {MYSQL_PORT}.")
        print("Повторная установка не требуется.")
        return finish_success(args)

    print(f"\nMySQL не отвечает на порту {MYSQL_PORT}.")

    if platform.system() == "Windows":
        services = find_windows_mysql_services()
        if services:
            print(f"   Найдены службы: {', '.join(services)}")

    print("\n1/2 Запуск службы MySQL...")
    if start_mysql_service() or mysql_is_running():
        print(f"\nMySQL запущен (порт {MYSQL_PORT}).")
        return finish_success(args)

    if args.start_only:
        print("\nНе удалось запустить службу MySQL.")
        if platform.system() == "Windows":
            print("Запустите PowerShell от имени администратора: net start MySQL80")
        return 1

    if not args.install:
        print("\nСлужба не запущена и установка не запрошена.")
        print("   python install_mysql.py              # попробовать запустить службу")
        print("   python install_mysql.py --install    # установить MySQL")
        print("   python install_mysql.py --install --setup --yes   # всё сразу")
        return 1

    if platform.system() == "Windows" and not is_admin():
        print("\nДля установки MySQL запустите терминал от имени администратора.")
        print_manual_windows_instructions()
        return 1
    if platform.system() == "Linux" and not is_admin():
        print("   Для установки понадобится sudo.")

    print("\n2/2 Установка MySQL...")
    if not install_mysql():
        return 1

    if not mysql_is_running():
        print("\nMySQL установлен, но сервер ещё не отвечает.")
        print("Перезагрузите компьютер или запустите службу вручную, затем:")
        print("   python setup_mysql.py")
        return 1

    print(f"\nMySQL доступен (порт {MYSQL_PORT}).")
    return finish_success(args)


if __name__ == "__main__":
    sys.exit(main())
