"""Настройка путей Qt до первого импорта PyQt5 (Windows и venv)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_qt() -> None:
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return

    try:
        import PyQt5
    except ImportError:
        return

    base = Path(PyQt5.__file__).resolve().parent
    plugin_dirs = [
        base / "Qt5" / "plugins",
        base / "Qt" / "plugins",
    ]

    for plugins_root in plugin_dirs:
        platforms = plugins_root / "platforms"
        if not platforms.is_dir():
            continue
        if not any(platforms.glob("qwindows.dll")) and not any(platforms.glob("libqwindows.so")):
            continue

        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins_root))

        if sys.platform == "win32":
            os.environ.setdefault("QT_QPA_PLATFORM", "windows")
            bin_dir = plugins_root.parent / "bin"
            if hasattr(os, "add_dll_directory"):
                for dll_dir in (bin_dir, platforms):
                    if dll_dir.is_dir():
                        os.add_dll_directory(str(dll_dir))
        break


configure_qt()
