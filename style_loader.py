"""Единая загрузка QSS для приложения."""
import os

# Корень проекта (рядом с main.py)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

STYLE_FILES = [
    "styles/base.qss",
    "styles/components/exercise_settings.qss",
]


def load_styles(app, root_dir=None):
    root = root_dir or ROOT_DIR
    style = ""
    for rel_path in STYLE_FILES:
        path = os.path.join(root, rel_path)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            style += f.read() + "\n"
    if style:
        app.setStyleSheet(style)
    return style
