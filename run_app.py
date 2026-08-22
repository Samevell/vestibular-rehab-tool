import sys
import traceback

import qt_bootstrap  # noqa: F401 — до импорта PyQt5

from app_paths import APP_TITLE, crash_log_path, is_frozen, setup_runtime


def main():
    print("\nЗапуск графического интерфейса...")
    setup_runtime()

    try:
        from PyQt5 import QtWidgets
        from style_loader import load_styles
        from main import MainWindow

        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName(APP_TITLE)
        load_styles(app)

        window = MainWindow()
        window.show()
        sys.exit(app.exec_())

    except Exception as e:
        print(f"Ошибка при запуске GUI: {e}")
        traceback.print_exc()
        try:
            setup_runtime()
            crash_log_path().write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        if not is_frozen():
            input("\nНажмите Enter для выхода...")
        sys.exit(1)


if __name__ == "__main__":
    main()
