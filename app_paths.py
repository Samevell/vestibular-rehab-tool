"""Пути к ресурсам приложения и каталогу данных пользователя."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "RehabTrainer"
APP_TITLE = "Тренажёр вестибулярного аппарата"
APP_VERSION = "1.0.0"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Рабочие данные: БД, аватары, калибровка, журнал ошибок."""
    if is_frozen():
        if sys.platform == "win32":
            root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            return Path(root) / APP_DIR_NAME
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
        return Path.home() / ".local" / "share" / APP_DIR_NAME
    return project_root() / "data"


def profiles_dir() -> Path:
    if is_frozen():
        return user_data_dir() / "calibration_profiles"
    return project_root() / "calibration_profiles"


def asset(relative: str) -> str:
    """Абсолютный путь к файлу из комплекта приложения (img, styles, sounds, data)."""
    rel = relative.replace("\\", "/").lstrip("./")
    return str(project_root() / rel)


def resolve_asset(path: str) -> str:
    if not path:
        return path
    candidate = Path(path)
    if candidate.is_file():
        return str(candidate)
    resolved = Path(asset(path))
    if resolved.is_file():
        return str(resolved)
    return path


def crash_log_path() -> Path:
    return user_data_dir() / "crash.log"


def setup_runtime() -> None:
    user_data_dir().mkdir(parents=True, exist_ok=True)
    profiles_dir().mkdir(parents=True, exist_ok=True)
