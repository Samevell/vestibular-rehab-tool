"""Единая загрузка QSS для приложения."""
from pathlib import Path

from app_paths import project_root

STYLE_FILES = [
    "styles/base.qss",
    "styles/components/exercise_settings.qss",
    "styles/components/startup.qss",
    "styles/components/user_profile.qss",
    "styles/components/app_settings.qss",
    "styles/components/history.qss",
    "styles/components/training.qss",
]


def load_styles(app, root_dir=None):
    root = Path(root_dir) if root_dir else project_root()
    style = ""
    for rel_path in STYLE_FILES:
        path = root / rel_path
        if not path.is_file():
            continue
        style += path.read_text(encoding="utf-8") + "\n"
    if style:
        app.setStyleSheet(style)
    return style
