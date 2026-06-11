"""Настройки подключения к MySQL (общие для приложения и setup_mysql)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).resolve().parent / "db_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 3306,
    "database": "trainer",
    "user": "root",
    "password": "pass",
}


def load_db_config() -> Dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            config.update(json.load(f))
    return config


def save_db_config(config: Dict[str, Any]) -> None:
    payload = {key: config.get(key, DEFAULT_CONFIG[key]) for key in DEFAULT_CONFIG}
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def mysql_connect_kwargs(*, database: str | None = None, include_database: bool = True) -> Dict[str, Any]:
    cfg = load_db_config()
    kwargs: Dict[str, Any] = {
        "host": cfg["host"],
        "port": int(cfg["port"]),
        "user": cfg["user"],
        "password": cfg["password"],
    }
    if include_database:
        kwargs["database"] = database if database is not None else cfg["database"]
    return kwargs
