import sys
import traceback
from datetime import datetime
from pathlib import Path
from PyQt5 import QtWidgets
from window_ui import Ui_MainWindow
from detect_thread import CameraThread
from ex_2 import CameraThread2
from ex_3 import CameraThread3
from ex_4 import CameraThread4
from ex_5 import CameraThread5
from ex_6 import CameraThread6
from ex_7 import CameraThread7
from ex_8 import CameraThread8
from ex_9 import CameraThread9
from PyQt5.QtGui import QImage, QPixmap
import cv2
from PyQt5.QtCore import Qt, QTimer, QSize, QEvent, QSettings
from PyQt5 import QtGui
from widgets.history_period import HistoryPeriodPopup
from widgets.user_avatar import UserAvatar
from widgets.camera_capture import CameraCaptureDialog, SettingsPreviewThread
from sound_manager import apply_audio_output, list_audio_outputs
from style_loader import load_styles
from analytics.recommend import recommend
from analytics.ui_binding import (
    apply_exercise_params,
    exercise_id_from_key,
    load_dict_to_ui_params,
    read_exercise_params,
)

from app_paths import APP_TITLE, asset, crash_log_path, setup_runtime
from storage import Database, avatar_file, save_avatar_pixmap
from app_settings import (
    KEY_AUDIO_OUTPUT,
    KEY_AUTOPAUSE,
    KEY_CAMERA,
    KEY_FULLSCREEN,
    KEY_MIRROR,
    KEY_SKELETON,
    KEY_VOLUME,
    audio_output,
    autopause_enabled,
    camera_index,
    list_cameras,
    is_fullscreen,
    is_mirror,
    set_value,
    show_skeleton,
    volume,
    volume_f,
)

# Перехватчик исключений
def exception_hook(exctype, value, traceback_obj):
    """Перехват исключений для отображения в консоли"""
    print(f"🚨 Критическая ошибка: {exctype.__name__}: {value}")
    traceback.print_exception(exctype, value, traceback_obj)
    try:
        setup_runtime()
        crash_log_path().write_text(
            "".join(traceback.format_exception(exctype, value, traceback_obj)),
            encoding="utf-8",
        )
    except Exception:
        pass

    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Critical)
    msg_box.setWindowTitle("Критическая ошибка")
    msg_box.setText(f"Произошла ошибка:\n{exctype.__name__}: {value}")
    msg_box.exec_()

    sys.exit(1)

sys.excepthook = exception_hook


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        try:
            print("=" * 50)
            print("🚀 Запуск тренажера вестибулярного аппарата")
            print("=" * 50)
            
            # Инициализация базы данных ПЕРЕД созданием UI
            print("🔄 Инициализация базы данных...")
            self.db = Database()
            
            self.current_user_id = None

            self.settings = QSettings("RehabTrainer", "VestibularApp")

            # пробуем загрузить последнего пользователя
            self.current_user_id = self.settings.value("current_user_id", type=int)

            if self.current_user_id:
                print(f"👤 Загружен пользователь ID={self.current_user_id}")
            else:
                print("👤 Пользователь не выбран")

            
            # Подключаем UI
            print("🔄 Инициализация пользовательского интерфейса...")
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
            self.setWindowTitle(APP_TITLE)
            icon_path = asset("img/app.ico")
            if Path(icon_path).is_file():
                self.setWindowIcon(QtGui.QIcon(icon_path))
            profile_shadow = QtWidgets.QGraphicsDropShadowEffect(self.ui.btn_current_user)
            profile_shadow.setBlurRadius(18)
            profile_shadow.setOffset(0, 1)
            profile_shadow.setColor(QtGui.QColor(0, 0, 0, 28))
            self.ui.btn_current_user.setGraphicsEffect(profile_shadow)
            self.ui.btn_current_user._radius = 33
            self.ui.label_current_user.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.ui.label_user_avatar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.ui.verticalLayout_startup_create.setAlignment(
                self.ui.icon_startup_create, Qt.AlignHCenter
            )
            self.ui.verticalLayout_user_profile_card.setAlignment(
                self.ui.avatar_user_profile, Qt.AlignHCenter
            )
            for pill in (
                self.ui.btn_user_profile_back,
                self.ui.btn_back_settings,
                self.ui.pushButton_3,
            ):
                shadow = QtWidgets.QGraphicsDropShadowEffect(pill)
                shadow.setBlurRadius(18)
                shadow.setOffset(0, 1)
                shadow.setColor(QtGui.QColor(0, 0, 0, 28))
                pill.setGraphicsEffect(shadow)
            self.ui.listWidget_startup_users.setFocusPolicy(Qt.NoFocus)
            self.ui.listWidget_startup_users.setMouseTracking(True)
            self.ui.listWidget_startup_users.viewport().setMouseTracking(True)
            self.ui.listWidget_startup_users.setCursor(Qt.PointingHandCursor)
            self.ui.listWidget_startup_users.viewport().setCursor(Qt.PointingHandCursor)
            self._hovered_startup_item = None
            self.ui.listWidget_startup_users.itemEntered.connect(self._on_startup_user_hovered)
            self.ui.listWidget_startup_users.viewport().installEventFilter(self)
            self.ui.listWidget_startup_users.currentItemChanged.connect(
                lambda _cur, _prev: self._refresh_startup_user_row_styles()
            )
            self.ui.tableWidget.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Stretch
            )
            self.ui.tableWidget.setEditTriggers(
                QtWidgets.QAbstractItemView.NoEditTriggers
            )
            self.ui.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.ui.tableWidget.setAlternatingRowColors(True)
            self.ui.verticalLayout_9.setStretch(2, 2)
            self.ui.verticalLayout_9.setStretch(3, 3)
            
            if self.db and hasattr(self.db, "is_connected") and not self.db.is_connected:
                print("⚠️ Не удалось открыть локальную базу SQLite.")
                print(f"   Файл: {getattr(self.db, 'db_path', 'неизвестно')}")
            
            # Устанавливаем группы для карточек упражнений
            self.ui.card_excersise_apple.setGroup("trainers")
            self.ui.card_excersise_apple_2.setGroup("trainers")
            self.ui.card_excersise_apple_3.setGroup("trainers")
            self.ui.card_excersise_apple_4.setGroup("trainers")
            self.ui.card_excersise_apple_5.setGroup("trainers")
            self.ui.card_excersise_apple_6.setGroup("trainers")
            self.ui.card_excersise_apple_7.setGroup("trainers")
            self.ui.card_excersise_apple_8.setGroup("trainers")
            self.ui.card_excersise_apple_9.setGroup("trainers")

            # Подключаем обработчики кнопок
            print("🔄 Подключение обработчиков кнопок...")
            self.ui.card_train_btn.clicked.connect(self.open_page_choose_ex)
            self.ui.card_settings_btn.clicked.connect(self.open_page_settings)
            self.ui.card_history_btn.clicked.connect(self.open_history_page)
            self.ui.pushButton_3.clicked.connect(self.open_main_page)
            self.ui.btn_back_choose_ex.clicked.connect(self.open_main_page)
            
            # Подключаем карточки упражнений
            self.ui.card_excersise_apple.clicked.connect(self.show_apple_ex_description)
            self.ui.card_excersise_apple_2.clicked.connect(self.show_ex_2_description)
            self.ui.card_excersise_apple_3.clicked.connect(self.show_ex_3_description)
            self.ui.card_excersise_apple_4.clicked.connect(self.show_ex_4_description)
            self.ui.card_excersise_apple_5.clicked.connect(self.show_ex_5_description)
            self.ui.card_excersise_apple_6.clicked.connect(self.show_ex_6_description)
            self.ui.card_excersise_apple_7.clicked.connect(self.show_ex_7_description)
            self.ui.card_excersise_apple_8.clicked.connect(self.show_ex_8_description)
            self.ui.card_excersise_apple_9.clicked.connect(self.show_ex_9_description)
            
            self.ui.btn_start_ex.clicked.connect(self.start_current_exercise)
            self.ui.btn_back_video.clicked.connect(self.stop_camera)
            self.ui.btn_back_video.raise_()
            self.ui.stacked_widget_main.raise_()
            self.ui.widget_bg_waves.sync_to_parent()
            self.ui.widget_bg_points.sync_to_parent()
            self.ui.stacked_widget_main.currentChanged.connect(self._sync_training_chrome)
            self._sync_training_chrome()
            self.ui.card_exit_btn.clicked.connect(self.close)
            self.ui.btn_back_settings.clicked.connect(self.open_main_page)
            self.ui.btn_startup_continue.clicked.connect(self.continue_with_startup_user)
            self.ui.btn_startup_new_user.clicked.connect(
                lambda: self.show_startup_create(first_entry=False)
            )
            self.ui.btn_startup_create.clicked.connect(self.create_startup_user)
            self.ui.btn_startup_back_to_select.clicked.connect(self.show_startup_select)
            self.ui.listWidget_startup_users.itemDoubleClicked.connect(
                lambda _item: self.continue_with_startup_user()
            )
            self.ui.lineEdit_startup_last_name.returnPressed.connect(
                self.create_startup_user
            )
            
            # Подключаем изменение выбора в комбобоксе
            self.ui.btn_current_user.clicked.connect(self.open_user_profile)
            self.ui.btn_user_profile_back.clicked.connect(self.open_main_page)
            self.ui.btn_switch_user.clicked.connect(self.show_startup_select)
            self.ui.btn_choose_avatar.clicked.connect(self.choose_user_avatar)
            self.ui.btn_capture_avatar.clicked.connect(self.capture_user_avatar)
            self.ui.btn_save_profile.clicked.connect(self.save_user_profile)
            self.ui.btn_delete_profile.clicked.connect(self.delete_selected_user)
            self.ui.checkBox_fullscreen.toggled.connect(self._on_fullscreen_toggled)
            self.ui.combo_camera.currentIndexChanged.connect(self._on_camera_changed)
            self.ui.combo_audio_output.currentIndexChanged.connect(self._on_audio_output_changed)
            self.ui.horizontalLayout_audio.setStretch(1, 1)
            self.ui.checkBox_mirror.toggled.connect(self._on_mirror_toggled)
            self.ui.slider_volume.valueChanged.connect(self._on_volume_changed)
            self.ui.checkBox_skeleton.toggled.connect(self._on_skeleton_toggled)
            self.ui.checkBox_autopause.toggled.connect(self._on_autopause_toggled)

            self._preview_thread = None
            self._preview_gen = 0
            self._settings_loading = False
            QTimer.singleShot(0, self._apply_fullscreen)
            
            # Настраиваем таблицу истории
            self.setup_history_table()
            self._make_window_resizable()
            self.setup_recommendation_buttons()
            
            self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_emty)

            self.load_users()
            self.apply_startup_flow()
            
            print("🔄 Загрузка изображений...")
            self._setup_example_images()
            
            # Устанавливаем начальные значения
            self.ui.spinBox_apple_count.setValue(12)
            self.ui.spinBox_apple_second.setValue(10)
            self.ui.spinBox_apple_count_2.setValue(5)
            self.ui.spinBox_apple_second_2.setValue(4)
            self.ui.spinBox_apple_count_3.setValue(5)
            
            self.current_exercise = None
            
            print("✅ MainWindow инициализирован успешно")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации MainWindow: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                None,
                "Ошибка инициализации",
                f"Не удалось инициализировать приложение:\n{str(e)}"
            )
            sys.exit(1)

    def setup_recommendation_buttons(self):
        """Кнопки назначения врача и рекомендаций на экране выбора упражнения."""
        icon_size = QSize(20, 20)
        font = QtGui.QFont()
        font.setPointSize(15)
        buttons_icons = (
            (self.ui.btn_save_baseline, asset("img/bookmark_icon.svg")),
            (self.ui.btn_apply_recommendation, asset("img/sparkles_icon.svg")),
            (self.ui.btn_restore_baseline, asset("img/reset_icon.svg")),
        )
        for btn, icon_path in buttons_icons:
            btn.setFont(font)
            btn.setIcon(QtGui.QIcon(icon_path))
            btn.setIconSize(icon_size)
            btn.setCursor(QtGui.QCursor(Qt.PointingHandCursor))

        self.ui.btn_save_baseline.clicked.connect(self.save_doctor_baseline_for_current)
        self.ui.btn_apply_recommendation.clicked.connect(
            self.apply_recommendation_for_current
        )
        self.ui.btn_restore_baseline.clicked.connect(
            self.restore_doctor_baseline_for_current
        )
        self.ui.stacked_widget_ex_choose.currentChanged.connect(
            self._update_prescription_panel_visibility
        )
        self._update_prescription_panel_visibility()

    def _update_prescription_panel_visibility(self):
        exercise_selected = (
            self.ui.stacked_widget_ex_choose.currentWidget() != self.ui.page_emty
        )
        self.ui.frame_prescription_actions.setVisible(exercise_selected)

    def _current_exercise_id(self):
        return exercise_id_from_key(self.current_exercise)

    def _require_user_and_exercise(self):
        if not self.current_user_id:
            QtWidgets.QMessageBox.warning(
                self, "Пользователь", "Выберите пользователя в настройках."
            )
            return None
        exercise_id = self._current_exercise_id()
        if not exercise_id:
            QtWidgets.QMessageBox.warning(
                self, "Упражнение", "Сначала выберите упражнение."
            )
            return None
        if not self.db:
            QtWidgets.QMessageBox.warning(self, "База данных", "База данных недоступна.")
            return None
        return exercise_id

    def save_doctor_baseline_for_current(self):
        exercise_id = self._require_user_and_exercise()
        if exercise_id is None:
            return

        params = read_exercise_params(self.ui, exercise_id)
        if self.db.save_doctor_baseline(self.current_user_id, exercise_id, params):
            QtWidgets.QMessageBox.information(
                self,
                "Назначение врача",
                f"Параметры упражнения {exercise_id} сохранены как назначение врача.",
            )
        else:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Не удалось сохранить назначение врача."
            )

    def restore_doctor_baseline_for_current(self):
        exercise_id = self._require_user_and_exercise()
        if exercise_id is None:
            return

        baseline = self.db.get_doctor_baseline(self.current_user_id, exercise_id)
        if not baseline:
            QtWidgets.QMessageBox.information(
                self,
                "Назначение врача",
                "Для этого упражнения назначение врача ещё не сохранено.",
            )
            return

        apply_exercise_params(self.ui, exercise_id, baseline, load_only=False)

    def apply_recommendation_for_current(self):
        exercise_id = self._require_user_and_exercise()
        if exercise_id is None:
            return

        baseline = self.db.get_doctor_baseline(self.current_user_id, exercise_id)
        if not baseline:
            QtWidgets.QMessageBox.information(
                self,
                "Рекомендация",
                "Сначала сохраните назначение врача для этого упражнения.",
            )
            return

        history = self.db.get_exercise_sessions(
            self.current_user_id, exercise_id, limit=6
        )
        result = recommend(exercise_id, baseline, history)

        ui_params = load_dict_to_ui_params(exercise_id, result.load)
        apply_exercise_params(self.ui, exercise_id, ui_params, load_only=True)

        if not result.sufficient_data:
            QtWidgets.QMessageBox.information(
                self,
                "Рекомендация",
                "Недостаточно данных по истории (нужно минимум 2 занятия).\n"
                "Используется назначение врача без изменений.",
            )
            return

        action = {-1: "упрощение", 0: "без изменений", 1: "усложнение"}[result.delta]
        metrics = result.metrics
        QtWidgets.QMessageBox.information(
            self,
            "Рекомендация",
            f"Рекомендация применена: {action}.\n"
            f"Средняя успешность: {metrics.s_bar:.1f}%\n"
            f"Тренд: {metrics.trend:+.1f} п.п.",
        )

    def setup_history_table(self):
        """Настройка таблицы и фильтров истории."""
        headers = [
            "Дата",
            "Упражнение",
            "Поймано",
            "Успешность",
            "Фон",
            "Балл",
        ]
        self.ui.tableWidget.setColumnCount(len(headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.ui.tableWidget.verticalHeader().setVisible(False)
        self.ui.tableWidget.setShowGrid(False)
        self.ui.tableWidget.setSortingEnabled(False)
        header = self.ui.tableWidget.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.setHighlightSections(False)
        header.setCursor(Qt.PointingHandCursor)
        header.sectionClicked.connect(self._on_history_header_clicked)
        for i in range(len(headers)):
            item = self.ui.tableWidget.horizontalHeaderItem(i)
            if item is not None:
                item.setTextAlignment(Qt.AlignCenter)

        self._history_sort_column = None
        self._history_sort_desc = True

        self.ui.combo_history_exercise.blockSignals(True)
        self.ui.combo_history_exercise.clear()
        self.ui.combo_history_exercise.addItem("Все упражнения", 0)
        for number in range(1, 10):
            self.ui.combo_history_exercise.addItem(f"Упражнение {number}", number)
        self.ui.combo_history_exercise.blockSignals(False)

        self._history_period = (None, None)
        self._history_period_popup = HistoryPeriodPopup(self)
        self._history_period_popup.periodChanged.connect(self._on_history_period_changed)
        self.ui.btn_history_period.clicked.connect(self._open_history_period)
        self._update_history_period_button()

        self.ui.combo_history_exercise.currentIndexChanged.connect(self._refresh_history_view)
        self.ui.chart_history_success.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.ui.chart_history_exercises.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self._history_records = []

    def _all_users(self):
        if self.db is None:
            return []
        return self.db.get_all_users()

    def _user_id_exists(self, user_id):
        if not user_id:
            return False
        return any(user["id"] == user_id for user in self._all_users())

    def _current_user_name(self):
        for user in self._all_users():
            if user["id"] == self.current_user_id:
                return f"{user['first_name']} {user['last_name']}"
        return ""

    def _set_current_user(self, user_id, display_name):
        self.current_user_id = user_id
        if user_id:
            self.settings.setValue("current_user_id", user_id)
            self.ui.label_current_user.setText(display_name)
        else:
            self.settings.setValue("current_user_id", None)
            self.ui.label_current_user.setText("Не выбран")

    def _apply_user_avatar(self, user_id=None):
        user_id = user_id if user_id is not None else self.current_user_id
        path = avatar_file(user_id) if user_id else None
        photo = str(path) if path is not None and path.exists() else ""
        self.ui.label_user_avatar.setPhotoPath(photo)
        self.ui.avatar_user_profile.setPhotoPath(photo)

    def open_user_profile(self):
        if not self._user_id_exists(self.current_user_id):
            self.apply_startup_flow()
            return
        user = self.db.get_user(self.current_user_id)
        if not user:
            self.apply_startup_flow()
            return
        self.ui.lineEdit_profile_first.setText(user["first_name"])
        self.ui.lineEdit_profile_last.setText(user["last_name"])
        self._apply_user_avatar(self.current_user_id)
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_user_profile)

    def save_user_profile(self):
        if not self.current_user_id or self.db is None:
            return
        first_name = self.ui.lineEdit_profile_first.text().strip()
        last_name = self.ui.lineEdit_profile_last.text().strip()
        if not first_name or not last_name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя и фамилию!")
            return
        if not self.db.update_user(self.current_user_id, first_name, last_name):
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось сохранить. Возможно, пациент с таким именем уже есть.",
            )
            return
        self._set_current_user(self.current_user_id, f"{first_name} {last_name}")
        self.load_users()
        self.open_main_page()

    def choose_user_avatar(self):
        if not self.current_user_id:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Выберите фото",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось открыть изображение.")
            return
        save_avatar_pixmap(self.current_user_id, pixmap)
        self._apply_user_avatar(self.current_user_id)

    def capture_user_avatar(self):
        if not self.current_user_id:
            return
        dialog = CameraCaptureDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        if dialog.result_pixmap is None or dialog.result_pixmap.isNull():
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Снимок не получен.")
            return
        save_avatar_pixmap(self.current_user_id, dialog.result_pixmap)
        self._apply_user_avatar(self.current_user_id)

    def apply_startup_flow(self):
        """Стартовый экран: создание при первом входе, иначе прошлый пациент."""
        users = self._all_users()
        if not users:
            self.current_user_id = None
            self.settings.setValue("current_user_id", None)
            self.show_startup_create(first_entry=True)
            return

        if self._user_id_exists(self.current_user_id):
            self.load_users()
            self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_main)
            return

        self.current_user_id = None
        self.settings.setValue("current_user_id", None)
        self.show_startup_select()

    def _style_startup_user_row(self, row, selected, hovered=False):
        if selected:
            row.setStyleSheet(
                "#startup_user_row {"
                "  background: #E8F8F7;"
                "  border: 1px solid #1dbeb7;"
                "  border-radius: 14px;"
                "}"
                "#startup_user_row_name {"
                "  background: transparent;"
                "  color: #2C3E50;"
                "  font-size: 18px;"
                "  font-weight: 600;"
                "}"
            )
        elif hovered:
            row.setStyleSheet(
                "#startup_user_row {"
                "  background: #F3FBFA;"
                "  border: 1px solid #1dbeb7;"
                "  border-radius: 14px;"
                "}"
                "#startup_user_row_name {"
                "  background: transparent;"
                "  color: #2C3E50;"
                "  font-size: 18px;"
                "  font-weight: 400;"
                "}"
            )
        else:
            row.setStyleSheet(
                "#startup_user_row {"
                "  background: #FFFFFF;"
                "  border: 1px solid #E8EEF2;"
                "  border-radius: 14px;"
                "}"
                "#startup_user_row_name {"
                "  background: transparent;"
                "  color: #2C3E50;"
                "  font-size: 18px;"
                "  font-weight: 400;"
                "}"
            )

    def _build_startup_user_row(self, display_name, user_id=None):
        row = QtWidgets.QWidget()
        row.setObjectName("startup_user_row")
        row.setAttribute(Qt.WA_StyledBackground, True)
        row.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(16, 10, 21, 10)
        layout.setSpacing(16)

        avatar = UserAvatar(row)
        avatar.setFixedSize(52, 52)
        avatar.setSvgFile(asset("img/user_icon.svg"))
        avatar.setMainColor("#1dbeb7")
        avatar.setCircleColor("#e8f8f7")
        if user_id:
            path = avatar_file(user_id)
            if path.exists():
                avatar.setPhotoPath(str(path))
        avatar.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        name = QtWidgets.QLabel(display_name, row)
        name.setObjectName("startup_user_row_name")
        name.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout.addWidget(avatar)
        layout.addWidget(name, 1)
        self._style_startup_user_row(row, False)
        return row

    def _refresh_startup_user_row_styles(self):
        list_widget = self.ui.listWidget_startup_users
        current = list_widget.currentItem()
        hovered = getattr(self, "_hovered_startup_item", None)
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            widget = list_widget.itemWidget(item)
            if widget is not None:
                self._style_startup_user_row(
                    widget, item is current, hovered=(item is hovered and item is not current)
                )

    def _on_startup_user_hovered(self, item):
        self._hovered_startup_item = item
        self._refresh_startup_user_row_styles()

    def eventFilter(self, obj, event):
        viewport = getattr(self.ui, "listWidget_startup_users", None)
        viewport = viewport.viewport() if viewport is not None else None
        if obj is viewport and event.type() == QEvent.Leave:
            self._hovered_startup_item = None
            self._refresh_startup_user_row_styles()
        return super().eventFilter(obj, event)

    def show_startup_select(self):
        self._stop_settings_preview()
        users = self._all_users()
        if not users:
            self.show_startup_create(first_entry=True)
            return

        self.ui.listWidget_startup_users.clear()
        self._hovered_startup_item = None
        selected_row = 0
        for index, user in enumerate(users):
            display_name = f"{user['first_name']} {user['last_name']}"
            item = QtWidgets.QListWidgetItem()
            item.setData(Qt.UserRole, user["id"])
            item.setData(int(Qt.UserRole) + 1, display_name)
            item.setSizeHint(QSize(0, 75))
            self.ui.listWidget_startup_users.addItem(item)
            self.ui.listWidget_startup_users.setItemWidget(
                item, self._build_startup_user_row(display_name, user["id"])
            )
            if self.current_user_id and user["id"] == self.current_user_id:
                selected_row = index

        if self.ui.listWidget_startup_users.count() > 0:
            self.ui.listWidget_startup_users.setCurrentRow(selected_row)
            self._refresh_startup_user_row_styles()

        self.ui.stacked_startup.setCurrentWidget(self.ui.page_startup_select)
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_startup)

    def show_startup_create(self, first_entry=False):
        users = self._all_users()
        is_first = first_entry or not users
        self.ui.label_startup_create_title.setText(
            "Первый вход" if is_first else "Новый пациент"
        )
        self.ui.btn_startup_back_to_select.setVisible(not is_first)
        self.ui.stacked_startup.setCurrentWidget(self.ui.page_startup_create)
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_startup)
        self.ui.lineEdit_startup_first_name.setFocus()

    def continue_with_startup_user(self):
        item = self.ui.listWidget_startup_users.currentItem()
        if item is None:
            QtWidgets.QMessageBox.warning(
                self, "Пациент не выбран", "Выберите пациента из списка."
            )
            return
        user_id = item.data(Qt.UserRole)
        display_name = item.data(int(Qt.UserRole) + 1) or "Пациент"
        self._set_current_user(user_id, display_name)
        self.load_users()
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_main)

    def create_startup_user(self):
        if self.db is None:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "База данных недоступна!")
            return

        first_name = self.ui.lineEdit_startup_first_name.text().strip()
        last_name = self.ui.lineEdit_startup_last_name.text().strip()
        if not first_name or not last_name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя и фамилию!")
            return

        user_id = self.db.get_or_create_user(first_name, last_name)
        if user_id is None:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка", "Не удалось сохранить пациента."
            )
            return

        self.ui.lineEdit_startup_first_name.clear()
        self.ui.lineEdit_startup_last_name.clear()
        self._set_current_user(user_id, f"{first_name} {last_name}")
        self.load_users()
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_main)

    def load_users(self):
        """Обновить имя текущего пациента в шапке."""
        if self.db is None:
            return
        name = self._current_user_name()
        self.ui.label_current_user.setText(name or "Не выбран")
        self._apply_user_avatar(self.current_user_id)


    def delete_selected_user(self):
        """Удаление текущего пациента"""
        user_id = self.current_user_id
        user_name = self._current_user_name()
        
        if not user_id:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите пользователя для удаления")
            return
        
        # Подтверждение
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить пользователя {user_name}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply != QtWidgets.QMessageBox.Yes:
            return
        
        success = self.db.delete_user(user_id)
        
        if not success:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось удалить пользователя")
            return
        
        # Если удалили текущего пользователя — сбрасываем
        if self.current_user_id == user_id:
            self.current_user_id = None
            self.settings.setValue("current_user_id", None)
            self.ui.label_current_user.setText("Не выбран")
        
        # Перезагружаем комбобокс
        self.load_users()
        
        QtWidgets.QMessageBox.information(self, "Успех", f"Пользователь {user_name} удален")
        if not self._user_id_exists(self.current_user_id):
            self.apply_startup_flow()

    def calculate_coefficient_ex1_ex2(self, apples_count, seconds_per_apple, caught_apples):
        """
        Расчет коэффициента для упражнений 1 и 2
        Новый подход: учитываем процент пойманных яблок и сложность (время)
        """
        if apples_count == 0 or seconds_per_apple == 0:
            return 0
        
        # 1. Процент пойманных яблок (от 0 до 1)
        success_rate = caught_apples / apples_count
        
        # 2. Коэффициент сложности: чем меньше времени на яблоко, тем сложнее
        # Базовое время: 10 секунд. Если меньше - коэффициент увеличивается
        if seconds_per_apple <= 5:
            # Очень сложно: 1-5 секунд на яблоко
            difficulty_factor = 2.0
        elif seconds_per_apple <= 10:
            # Средняя сложность: 6-10 секунд
            difficulty_factor = 1.5
        elif seconds_per_apple <= 15:
            # Легко: 11-15 секунд
            difficulty_factor = 1.2
        else:
            # Очень легко: больше 15 секунд
            difficulty_factor = 1.0
        
        # 3. Итоговый коэффициент = успешность × сложность
        coefficient = success_rate * difficulty_factor
        
        # Ограничиваем коэффициент от 0 до 2
        coefficient = max(0, min(coefficient, 2.0))
        
        print(f"📊 Расчет коэффициента: успешность={success_rate:.2f}, сложность={difficulty_factor}, итог={coefficient:.2f}")
        return round(coefficient, 2)
    
    def calculate_coefficient_ex3(self, apples_count, speed, caught_apples):
        """
        Расчет коэффициента для упражнения 3
        Учитываем процент пойманных яблок и скорость
        """
        if apples_count == 0:
            return 0
        
        # 1. Процент пойманных яблок (от 0 до 1)
        success_rate = caught_apples / apples_count
        
        # 2. Коэффициент скорости
        speed_multipliers = {
            'Медленно': 1.0,
            'Средне': 1.5,
            'Быстро': 2.0
        }
        
        speed_multiplier = speed_multipliers.get(speed, 1.0)
        
        # 3. Итоговый коэффициент = успешность × скорость
        coefficient = success_rate * speed_multiplier
        
        # Ограничиваем коэффициент от 0 до 2
        coefficient = max(0, min(coefficient, 2.0))
        
        print(f"📊 Расчет коэффициента (упр.3): успешность={success_rate:.2f}, скорость={speed} (множ.={speed_multiplier}), итог={coefficient:.2f}")
        return round(coefficient, 2)
    
    def calculate_coefficient_ex4(self, objects_count, speed, caught_objects):
        """Расчет коэффициента для упражнения 4"""
        if objects_count == 0:
            return 0
        
        success_rate = caught_objects / objects_count
        speed_multipliers = {
            'Медленно': 1.0,
            'Средне': 1.5,
            'Быстро': 2.0
        }
        speed_factor = speed_multipliers.get(speed, 1.0)
        coefficient = success_rate * speed_factor
        coefficient = max(0, min(coefficient, 2.0))
        
        return round(coefficient, 2)
    
    def calculate_coefficient_ex5(self, objects_count, speed, caught_objects):
        """Расчет коэффициента для упражнения 5"""
        if objects_count == 0:
            return 0
        
        success_rate = caught_objects / objects_count
        speed_multipliers = {
            'Медленно': 1.0,
            'Средне': 1.5,
            'Быстро': 2.0
        }
        speed_factor = speed_multipliers.get(speed, 1.0)
        coefficient = success_rate * speed_factor
        coefficient = max(0, min(coefficient, 2.0))
        
        return round(coefficient, 2)
    
    def calculate_coefficient_ex7(self, objects_count, neck_range, caught_objects):
        """Расчет коэффициента для упражнения 7"""
        if objects_count == 0:
            return 0
        
        success_rate = caught_objects / objects_count
        
        range_multipliers = {
            '15°': 1.0,
            '20°': 1.5
        }
        
        range_factor = range_multipliers.get(neck_range, 1.0)
        coefficient = success_rate * range_factor
        coefficient = max(0, min(coefficient, 2.0))
        
        return round(coefficient, 2)
    
    def calculate_coefficient_ex8(self, objects_count, speed, color_interval, caught_objects):
        """Расчет коэффициента для упражнения 8"""
        if objects_count == 0:
            return 0
        
        success_rate = caught_objects / objects_count
        
        # Коэффициент скорости
        speed_multipliers = {
            'Медленно': 1.0,
            'Средне': 1.5,
            'Быстро': 2.0
        }
        
        speed_factor = speed_multipliers.get(speed, 1.0)
        
        # Коэффициент интервала смены цвета (чем меньше интервал, тем сложнее)
        if color_interval <= 1:
            color_factor = 2.0
        elif color_interval <= 2:
            color_factor = 1.5
        elif color_interval <= 3:
            color_factor = 1.2
        else:
            color_factor = 1.0
        
        coefficient = success_rate * ((speed_factor + color_factor) / 2)
        coefficient = max(0, min(coefficient, 2.0))
        
        return round(coefficient, 2)
    
    def calculate_coefficient_ex9(self, objects_count, speed, color_interval, caught_objects):
        """Расчет коэффициента для упражнения 9"""
        if objects_count == 0:
            return 0
        
        success_rate = caught_objects / objects_count
        
        speed_multipliers = {
            'Медленно': 1.0,
            'Средне': 1.5,
            'Быстро': 2.0
        }
        speed_factor = speed_multipliers.get(speed, 1.0)
        
        if color_interval <= 1:
            color_factor = 2.0
        elif color_interval <= 2:
            color_factor = 1.5
        elif color_interval <= 3:
            color_factor = 1.2
        else:
            color_factor = 1.0
        
        coefficient = success_rate * ((speed_factor + color_factor) / 2)
        coefficient = max(0, min(coefficient, 2.0))
        
        return round(coefficient, 2)
    
    def calculate_total_score(self, objects_count, caught_objects, coefficient):
        """Расчет общего балла"""
        max_possible_score = objects_count * 10
        success_percentage = caught_objects / objects_count if objects_count > 0 else 0
        base_score = max_possible_score * success_percentage
        total_score = base_score * coefficient
        
        return round(total_score, 2)

    # ==================== Методы открытия упражнений ====================
    
    def open_exercise_page1(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        difficulty = self.ui.spinBox_apple_count.value()
        seconds = self.ui.spinBox_apple_second.value()
        background = self.ui.comboBox_fon_apple.currentText()
        sound = self.ui.comboBox_sound_apple.currentText()
        
        self.exercise_params = {
            'type': 1,
            'difficulty': difficulty,
            'seconds': seconds,
            'background': background,
            'sound': sound
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread(difficulty, seconds, background, sound, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()

    def open_exercise_page2(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        difficulty = self.ui.spinBox_apple_count_2.value()
        seconds = self.ui.spinBox_apple_second_2.value()
        background = self.ui.comboBox_fon_apple_2.currentText()
        
        self.exercise_params = {
            'type': 2,
            'difficulty': difficulty,
            'seconds': seconds,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread2(difficulty, seconds, background, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()

    def open_exercise_page3(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        difficulty = self.ui.spinBox_apple_count_3.value()
        speed = self.ui.comboBox_speed_apple_3.currentText()
        background = self.ui.comboBox_fon_apple_3.currentText()
        
        self.exercise_params = {
            'type': 3,
            'difficulty': difficulty,
            'speed': speed,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread3(difficulty, speed, background, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    def open_exercise_page4(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        
        objects_count = self.ui.spinBox_ex4_count.value()
        time_sec = self.ui.spinBox_ex4_time.value()
        speed = self.ui.comboBox_ex4_speed.currentText()
        background = self.ui.comboBox_ex4_fon.currentText()
        
        self.exercise_params = {
            'type': 4,
            'objects_count': objects_count,
            'time_sec': time_sec,
            'speed': speed,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread4(objects_count, time_sec, speed, background, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    def open_exercise_page5(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        
        objects_count = self.ui.spinBox_ex5_count.value()
        time_sec = self.ui.spinBox_ex5_time.value()
        speed = self.ui.comboBox_ex5_speed.currentText()
        background = self.ui.comboBox_ex5_fon.currentText()
        
        self.exercise_params = {
            'type': 5,
            'objects_count': objects_count,
            'time_sec': time_sec,
            'speed': speed,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread5(objects_count, time_sec, speed, background, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    def open_exercise_page6(self):
        """Заглушка для упражнения 6"""
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        
        objects_count = self.ui.spinBox_ex6_count.value()
        time_sec = self.ui.spinBox_ex6_time.value()
        background = self.ui.comboBox_ex6_fon.currentText()
        
        self.exercise_params = {
            'type': 6,
            'objects_count': objects_count,
            'time_sec': time_sec,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread6(objects_count, time_sec, background, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    def open_exercise_page7(self):
        """Заглушка для упражнения 7"""
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        
        objects_count = self.ui.spinBox_ex7_count.value()
        time_sec = self.ui.spinBox_ex7_time.value()
        neck_range = self.ui.comboBox_ex7_neck.currentText()
        background = self.ui.comboBox_ex7_fon.currentText()
        
        self.exercise_params = {
            'type': 7,
            'objects_count': objects_count,
            'time_sec': time_sec,
            'neck_range': neck_range,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread7(objects_count, time_sec, neck_range, background, user_id=user_id)
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    def open_exercise_page8(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        
        objects_count = self.ui.spinBox_ex8_count.value()
        color_interval = self.ui.spinBox_ex8_color_interval.value()
        speed = self.ui.comboBox_ex8_speed.currentText()
        background = self.ui.comboBox_ex8_fon.currentText()
        time_sec = max(objects_count * color_interval, 30)
        
        self.exercise_params = {
            'type': 8,
            'objects_count': objects_count,
            'time_sec': time_sec,
            'color_interval': color_interval,
            'speed': speed,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread8(
            objects_count, time_sec, color_interval, speed, background, user_id=user_id
        )
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    def open_exercise_page9(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_ex)
        
        objects_count = self.ui.spinBox_ex9_count.value()
        color_interval = self.ui.spinBox_ex9_color_interval.value()
        speed = self.ui.comboBox_ex9_speed.currentText()
        background = self.ui.comboBox_ex9_fon.currentText()
        time_sec = max(objects_count * color_interval, 30)
        
        self.exercise_params = {
            'type': 9,
            'objects_count': objects_count,
            'time_sec': time_sec,
            'color_interval': color_interval,
            'speed': speed,
            'background': background
        }
        
        user_id = self.current_user_id if self.current_user_id is not None else 0
        self.thread = CameraThread9(
            objects_count, color_interval, speed, background, user_id=user_id
        )
        self.thread.frame_signal.connect(self.update_frame)
        self.thread.finished.connect(self.on_exercise_finished)
        self.thread.start()
    
    # ==================== Обработчики завершения упражнений ====================
    
    def on_exercise_finished(self):
        """Обработка завершения упражнения с сохранением результатов"""
        print("🎯 Упражнение завершено")
        
        caught_objects = self.thread.score if hasattr(self.thread, 'score') else 0
        print(f"📊 Поймано объектов: {caught_objects}")
        
        if self.current_user_id is None:
            QtWidgets.QMessageBox.warning(
                self, 
                "Ошибка", 
                "Сначала выберите пользователя из списка!"
            )
            self.stop_camera()
            return
        
        exercise_type = self.exercise_params['type']
        
        try:
            saving_msg = QtWidgets.QMessageBox()
            saving_msg.setWindowTitle("Сохранение")
            saving_msg.setText("Сохранение результатов...")
            saving_msg.setStandardButtons(QtWidgets.QMessageBox.NoButton)
            saving_msg.show()
            QtWidgets.QApplication.processEvents()
            
            success = False
            
            # Упражнение 1
            if exercise_type == 1:
                objects_count = self.exercise_params['difficulty']
                seconds_per_object = self.exercise_params['seconds']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex1_ex2(
                    objects_count, seconds_per_object, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_1(
                    self.current_user_id, objects_count, seconds_per_object, 
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 2
            elif exercise_type == 2:
                objects_count = self.exercise_params['difficulty']
                seconds_per_object = self.exercise_params['seconds']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex1_ex2(
                    objects_count, seconds_per_object, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_2(
                    self.current_user_id, objects_count, seconds_per_object, 
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 3
            elif exercise_type == 3:
                objects_count = self.exercise_params['difficulty']
                speed = self.exercise_params['speed']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex3(
                    objects_count, speed, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_3(
                    self.current_user_id, objects_count, speed, 
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 4
            elif exercise_type == 4:
                objects_count = self.exercise_params['objects_count']
                time_sec = self.exercise_params['time_sec']
                speed = self.exercise_params['speed']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex4(
                    objects_count, speed, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_4(
                    self.current_user_id, objects_count, time_sec, speed, 
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 5
            elif exercise_type == 5:
                objects_count = self.exercise_params['objects_count']
                time_sec = self.exercise_params['time_sec']
                speed = self.exercise_params['speed']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex5(
                    objects_count, speed, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_5(
                    self.current_user_id, objects_count, time_sec, speed, 
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 6
            elif exercise_type == 6:
                objects_count = self.exercise_params['objects_count']
                time_sec = self.exercise_params['time_sec']
                background = self.exercise_params['background']
                
                coefficient = 1.0  # Простой коэффициент для упражнения 6
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_6(
                    self.current_user_id, objects_count, time_sec,
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 7
            elif exercise_type == 7:
                objects_count = self.exercise_params['objects_count']
                time_sec = self.exercise_params['time_sec']
                neck_range = self.exercise_params['neck_range']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex7(
                    objects_count, neck_range, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_7(
                    self.current_user_id, objects_count, time_sec, neck_range, 
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 8
            elif exercise_type == 8:
                objects_count = self.exercise_params['objects_count']
                time_sec = self.exercise_params['time_sec']
                color_interval = self.exercise_params['color_interval']
                speed = self.exercise_params['speed']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex8(
                    objects_count, speed, color_interval, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_8(
                    self.current_user_id, objects_count, time_sec, color_interval, speed,
                    background, caught_objects, coefficient, total_score
                )
            
            # Упражнение 9
            elif exercise_type == 9:
                objects_count = self.exercise_params['objects_count']
                time_sec = self.exercise_params['time_sec']
                color_interval = self.exercise_params['color_interval']
                speed = self.exercise_params['speed']
                background = self.exercise_params['background']
                
                coefficient = self.calculate_coefficient_ex9(
                    objects_count, speed, color_interval, caught_objects
                )
                total_score = self.calculate_total_score(
                    objects_count, caught_objects, coefficient
                )
                
                success = self.db.save_exercise_9(
                    self.current_user_id, objects_count, time_sec, speed,
                    background, caught_objects, coefficient, total_score
                )
            
            saving_msg.close()
            
            objects_count_val = self.exercise_params.get('objects_count') or self.exercise_params.get('difficulty', 0)
            msg = f"🎉 Упражнение {exercise_type} завершено!\n\n"
            msg += f"Всего объектов: {objects_count_val}\n"
            msg += f"Поймано: {caught_objects}\n"
            msg += f"Процент успеха: {(caught_objects/objects_count_val*100):.1f}%\n"
            msg += f"Коэффициент: {coefficient}\n"
            msg += f"Итоговый балл: {total_score}\n\n"
            
            if success:
                msg += "✅ Результаты сохранены в базу данных."
            else:
                msg += "⚠️ Результаты НЕ сохранены в базу данных."
            
            QtWidgets.QMessageBox.information(self, "Результаты", msg)
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении результатов: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить результаты:\n{str(e)}"
            )

    # ==================== Навигация ====================
    
    def open_page_choose_ex(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_choose_ex)
        self._restore_selected_exercise()

    def _exercise_choice_widgets(self):
        return {
            "ex1": (self.ui.page_apples, self.ui.card_excersise_apple),
            "ex2": (self.ui.page_ex2, self.ui.card_excersise_apple_2),
            "ex3": (self.ui.page_ex3, self.ui.card_excersise_apple_3),
            "ex4": (self.ui.page_ex4, self.ui.card_excersise_apple_4),
            "ex5": (self.ui.page_ex5, self.ui.card_excersise_apple_5),
            "ex6": (self.ui.page_ex6, self.ui.card_excersise_apple_6),
            "ex7": (self.ui.page_ex7, self.ui.card_excersise_apple_7),
            "ex8": (self.ui.page_ex8, self.ui.card_excersise_apple_8),
            "ex9": (self.ui.page_ex9, self.ui.card_excersise_apple_9),
        }

    def _restore_selected_exercise(self):
        choice = self._exercise_choice_widgets().get(self.current_exercise)
        if choice is None:
            return
        page, card = choice
        self.ui.stacked_widget_ex_choose.setCurrentWidget(page)
        card.select()
    
    def _apply_fullscreen(self):
        if is_fullscreen():
            self.showFullScreen()
        elif self.isFullScreen():
            self.showNormal()
            self.showMaximized()

    def _load_settings_ui(self):
        self._settings_loading = True
        self.ui.checkBox_fullscreen.setChecked(is_fullscreen())
        self.ui.checkBox_mirror.setChecked(is_mirror())
        self.ui.slider_volume.setValue(volume())
        self.ui.label_volume_value.setText(f"{volume()}%")
        self.ui.checkBox_skeleton.setChecked(show_skeleton())
        self.ui.checkBox_autopause.setChecked(autopause_enabled())
        current = camera_index()
        cameras = list_cameras()
        self.ui.combo_camera.clear()
        if not cameras:
            self.ui.combo_camera.addItem("Камеры не найдены", None)
            self.ui.combo_camera.setEnabled(False)
        else:
            self.ui.combo_camera.setEnabled(True)
            selected = 0
            available = []
            for row, (index, name) in enumerate(cameras):
                self.ui.combo_camera.addItem(name, index)
                available.append(index)
                if index == current:
                    selected = row
            self.ui.combo_camera.setCurrentIndex(selected)
            if current not in available:
                set_value(KEY_CAMERA, int(available[0]))
        self._populate_audio_outputs()
        self._settings_loading = False
        apply_audio_output(audio_output())

    def _start_settings_preview(self):
        self._stop_settings_preview()
        index = self.ui.combo_camera.currentData()
        if index is None:
            self.ui.label_camera_preview.setPixmap(QPixmap())
            self.ui.label_camera_preview.setText("Камера не найдена")
            return
        self.ui.label_camera_preview.setPixmap(QPixmap())
        self.ui.label_camera_preview.setText("Подключение камеры...")
        self._preview_gen += 1
        gen = self._preview_gen
        thread = SettingsPreviewThread(int(index), self)
        thread.frame_ready.connect(
            lambda image, current=gen: self._on_preview_frame(image, current)
        )
        thread.status.connect(
            lambda text, current=gen: self._on_preview_status(text, current)
        )
        self._preview_thread = thread
        thread.start()

    def _stop_settings_preview(self):
        thread = getattr(self, "_preview_thread", None)
        if thread is None:
            return
        self._preview_thread = None
        self._preview_gen += 1
        try:
            thread.frame_ready.disconnect()
            thread.status.disconnect()
        except TypeError:
            pass
        thread.stop()
        thread.finished.connect(thread.deleteLater)
        if thread.isRunning():
            thread.wait(50)

    def _on_preview_frame(self, image, gen):
        if gen != getattr(self, "_preview_gen", 0):
            return
        pixmap = QPixmap.fromImage(image).scaled(
            self.ui.label_camera_preview.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.ui.label_camera_preview.setPixmap(pixmap)

    def _on_preview_status(self, text, gen):
        if gen != getattr(self, "_preview_gen", 0):
            return
        if text:
            self.ui.label_camera_preview.setPixmap(QPixmap())
            self.ui.label_camera_preview.setText(text)

    def _on_fullscreen_toggled(self, checked):
        if self._settings_loading:
            return
        set_value(KEY_FULLSCREEN, bool(checked))
        self._apply_fullscreen()

    def _on_camera_changed(self, _index):
        if self._settings_loading:
            return
        cam = self.ui.combo_camera.currentData()
        if cam is None:
            return
        set_value(KEY_CAMERA, int(cam))
        self._start_settings_preview()

    def _populate_audio_outputs(self):
        current = audio_output()
        self.ui.combo_audio_output.clear()
        selected = 0
        for row, (label, device_id) in enumerate(list_audio_outputs()):
            self.ui.combo_audio_output.addItem(label, device_id)
            if device_id == current:
                selected = row
        if current and selected == 0:
            self.ui.combo_audio_output.addItem(current, current)
            selected = self.ui.combo_audio_output.count() - 1
        self.ui.combo_audio_output.setCurrentIndex(selected)

    def _on_audio_output_changed(self, _index):
        if self._settings_loading:
            return
        device_id = self.ui.combo_audio_output.currentData()
        if device_id is None:
            return
        set_value(KEY_AUDIO_OUTPUT, str(device_id))
        apply_audio_output(str(device_id))

    def _on_mirror_toggled(self, checked):
        if self._settings_loading:
            return
        set_value(KEY_MIRROR, bool(checked))

    def _on_volume_changed(self, value):
        self.ui.label_volume_value.setText(f"{value}%")
        if self._settings_loading:
            return
        set_value(KEY_VOLUME, int(value))
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(volume_f())
        except Exception:
            pass

    def _on_skeleton_toggled(self, checked):
        if self._settings_loading:
            return
        set_value(KEY_SKELETON, bool(checked))

    def _on_autopause_toggled(self, checked):
        if self._settings_loading:
            return
        set_value(KEY_AUTOPAUSE, bool(checked))

    def open_page_settings(self):
        self._load_settings_ui()
        self.ui.label_camera_preview.setPixmap(QPixmap())
        self.ui.label_camera_preview.setText("Подключение камеры...")
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_settings)
        QTimer.singleShot(0, self._start_settings_preview)

    def open_main_page(self):
        self._stop_settings_preview()
        if not self._user_id_exists(self.current_user_id):
            self.apply_startup_flow()
            return
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_main)
    
    # ==================== Отображение описаний упражнений ====================
    
    def show_apple_ex_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_apples)
        self.current_exercise = 'ex1'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_2_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex2)
        self.current_exercise = 'ex2'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_3_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex3)
        self.current_exercise = 'ex3'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")
    
    def show_ex_4_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex4)
        self.current_exercise = 'ex4'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_5_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex5)
        self.current_exercise = 'ex5'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_6_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex6)
        self.current_exercise = 'ex6'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_7_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex7)
        self.current_exercise = 'ex7'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_8_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex8)
        self.current_exercise = 'ex8'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")

    def show_ex_9_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_ex9)
        self.current_exercise = 'ex9'
        print(f"📌 Выбрано упражнение: {self.current_exercise}")
    
    def start_current_exercise(self):
        """Запуск выбранного упражнения"""
        if self.current_exercise is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Упражнение не выбрано",
                "Пожалуйста, сначала выберите упражнение из списка слева."
            )
            return
        
        # Проверка выбора пользователя
        if self.current_user_id is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Пользователь не выбран",
                "Пожалуйста, выберите пользователя из списка на главной странице."
            )
            return
        
        # Запуск соответствующего упражнения
        if self.current_exercise == 'ex1':
            self.open_exercise_page1()
        elif self.current_exercise == 'ex2':
            self.open_exercise_page2()
        elif self.current_exercise == 'ex3':
            self.open_exercise_page3()
        elif self.current_exercise == 'ex4':
            self.open_exercise_page4()
        elif self.current_exercise == 'ex5':
            self.open_exercise_page5()
        elif self.current_exercise == 'ex6':
            self.open_exercise_page6()
        elif self.current_exercise == 'ex7':
            self.open_exercise_page7()
        elif self.current_exercise == 'ex8':
            self.open_exercise_page8()
        elif self.current_exercise == 'ex9':
            self.open_exercise_page9()

    def _setup_example_images(self):
        files = (
            (self.ui.lable_apple_example_img, asset("img/eex1.png")),
            (self.ui.lable_apple_example_img_2, asset("img/eex2.png")),
            (self.ui.lable_apple_example_img_3, asset("img/eex3.png")),
            (self.ui.lable_apple_example_img_4, asset("img/eex4.png")),
            (self.ui.lable_apple_example_img_5, asset("img/eex5.png")),
            (self.ui.lable_apple_example_img_6, asset("img/eex6.png")),
            (self.ui.lable_apple_example_img_7, asset("img/eex7.png")),
            (self.ui.lable_apple_example_img_8, asset("img/eex8.png")),
            (self.ui.lable_apple_example_img_9, asset("img/eex9.png")),
        )
        for widget, path in files:
            pixmap = QPixmap(path)
            if hasattr(widget, "setSource"):
                widget.setSource(pixmap)
            elif not pixmap.isNull():
                widget.setPixmap(pixmap)
            parent = widget.parentWidget()
            layout = parent.layout() if parent is not None else None
            if layout is None:
                continue
            index = layout.indexOf(widget)
            if index < 0:
                continue
            layout.setStretch(index, 1)
            for neighbor in (index - 1, index + 1):
                if neighbor < 0 or neighbor >= layout.count():
                    continue
                spacer = layout.itemAt(neighbor).spacerItem()
                if spacer is None:
                    continue
                spacer.changeSize(20, 8, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)

    def resizeEvent(self, event):
        self._adapt_layouts()
        self._sync_backgrounds()
        super().resizeEvent(event)

    def _make_window_resizable(self):
        expanding = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        ignored = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored
        )
        for stack in (
            self.ui.stacked_widget_main,
            self.ui.stacked_widget_ex_choose,
        ):
            if stack is None:
                continue
            stack.setSizePolicy(expanding)
            for index in range(stack.count()):
                page = stack.widget(index)
                if page is not None:
                    page.setSizePolicy(ignored)
        self.setMinimumSize(860, 540)
        self._main_cards_compact = None
        self.ui.listWidget_startup_users.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.ui.verticalLayout_startup_select.setStretch(1, 1)
        self.ui.btn_startup_continue.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.ui.btn_startup_new_user.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )

    def _adapt_layouts(self):
        self._adapt_history_layout()
        self._adapt_settings_layout()
        self._adapt_main_cards()

    def _adapt_settings_layout(self):
        cols = getattr(self.ui, "horizontalLayout_settings_cols", None)
        if cols is None:
            return
        cols.setDirection(
            QtWidgets.QBoxLayout.LeftToRight
            if self.width() >= 980
            else QtWidgets.QBoxLayout.TopToBottom
        )

    def _adapt_main_cards(self):
        grid = getattr(self.ui, "gridLayout", None)
        if grid is None:
            return
        compact = self.width() < 1000
        if getattr(self, "_main_cards_compact", None) == compact:
            return
        self._main_cards_compact = compact
        cards = (
            self.ui.card_train_btn,
            self.ui.card_history_btn,
            self.ui.card_settings_btn,
            self.ui.card_exit_btn,
        )
        for card in cards:
            grid.removeWidget(card)
        if compact:
            grid.addWidget(self.ui.card_train_btn, 0, 1)
            grid.addWidget(self.ui.card_history_btn, 0, 2)
            grid.addWidget(self.ui.card_settings_btn, 1, 1)
            grid.addWidget(self.ui.card_exit_btn, 1, 2)
        else:
            grid.addWidget(self.ui.card_train_btn, 0, 1)
            grid.addWidget(self.ui.card_history_btn, 0, 2)
            grid.addWidget(self.ui.card_settings_btn, 0, 3)
            grid.addWidget(self.ui.card_exit_btn, 0, 4)

    def _sync_backgrounds(self):
        self.ui.widget_bg_waves.sync_to_parent()
        self.ui.widget_bg_points.sync_to_parent()
        if self.ui.stacked_widget_main.currentWidget() is self.ui.page_ex:
            self.ui.stacked_widget_main.raise_()
            self.ui.btn_back_video.raise_()

    def _sync_training_chrome(self, *_args):
        training = self.ui.stacked_widget_main.currentWidget() is self.ui.page_ex
        self.ui.widget_bg_waves.setVisible(not training)
        self.ui.widget_bg_points.setVisible(not training)
        self.ui.stacked_widget_main.raise_()
        if training:
            self.ui.btn_back_video.raise_()

    def _adapt_history_layout(self):
        charts = getattr(self.ui, "horizontalLayout_history_charts", None)
        if charts is not None:
            charts.setDirection(
                QtWidgets.QBoxLayout.LeftToRight
                if self.width() >= 1100
                else QtWidgets.QBoxLayout.TopToBottom
            )

    def update_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        q_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        target = self.ui.label_video.size()
        if target.width() < 2 or target.height() < 2:
            return
        scaled = pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(target)
        canvas.fill(QtGui.QColor("#111111"))
        painter = QtGui.QPainter(canvas)
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
        self.ui.label_video.setPixmap(canvas)

    def closeEvent(self, event):
        """Закрытие соединения с БД при выходе"""
        self._stop_settings_preview()
        if self.db:
            self.db.close()
        event.accept()
        
    def stop_camera(self):
        if hasattr(self, 'thread'):
            self.thread.stop()
            self.thread.wait()
        self.open_page_choose_ex()

    def open_history_page(self):
        """Открытие страницы истории тренировок"""
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page)
        self._adapt_history_layout()
        self.load_history()

    @staticmethod
    def _history_success(record):
        total = record.get("total_apples") or 0
        caught = record.get("caught_apples") or 0
        if total <= 0:
            return 0.0
        return caught / total * 100.0

    @staticmethod
    def _history_date(record):
        value = record.get("exercise_date")
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%d.%m.%Y %H:%M"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    def _filtered_history(self, records, *, exercise=True, period=True):
        result = list(records)
        if exercise:
            exercise_id = self.ui.combo_history_exercise.currentData()
            if exercise_id:
                result = [row for row in result if int(row.get("exercise_id") or 0) == int(exercise_id)]
        if period:
            start, end = getattr(self, "_history_period", (None, None))
            if start is not None and end is not None:
                start_dt = datetime(start.year(), start.month(), start.day())
                end_dt = datetime(end.year(), end.month(), end.day(), 23, 59, 59)
                filtered = []
                for row in result:
                    moment = self._history_date(row)
                    if moment is None or start_dt <= moment <= end_dt:
                        filtered.append(row)
                result = filtered
        return result

    def _open_history_period(self):
        start, end = self._history_period
        self._history_period_popup.show_for(self.ui.btn_history_period, start, end)

    def _on_history_period_changed(self, start, end):
        self._history_period = (start, end)
        self._update_history_period_button()
        self._refresh_history_view()

    def _update_history_period_button(self):
        start, end = self._history_period
        if start is not None and end is not None:
            if start == end:
                text = start.toString("dd.MM.yyyy")
            else:
                text = f"{start.toString('dd.MM.yyyy')} — {end.toString('dd.MM.yyyy')}"
        else:
            text = "Всё время"
        self.ui.btn_history_period.setText(text)

    def _refresh_history_view(self):
        records = getattr(self, "_history_records", [])
        view_records = self._filtered_history(records, exercise=True, period=True)
        bar_records = self._filtered_history(records, exercise=False, period=True)

        line_points = []
        chronological = list(reversed(view_records))[-30:]
        for row in chronological:
            moment = self._history_date(row)
            label = moment.strftime("%d.%m") if moment else ""
            line_points.append((label, self._history_success(row)))
        self.ui.chart_history_success.set_points(line_points)

        averages = {}
        counts = {}
        for row in bar_records:
            name = row.get("exercise_type") or "Упражнение"
            averages[name] = averages.get(name, 0.0) + self._history_success(row)
            counts[name] = counts.get(name, 0) + 1
        bars = []
        for number in range(1, 10):
            name = f"Упражнение {number}"
            if counts.get(name):
                bars.append((f"Упр. {number}", averages[name] / counts[name]))
        self.ui.chart_history_exercises.set_bars(bars)
        self._fill_history_table(self._sort_history_records(view_records))

    def _history_sort_key(self, record):
        column = self._history_sort_column
        if column == 0:
            return self._history_date(record) or datetime.min
        if column == 1:
            return (int(record.get("exercise_id") or 0), record.get("exercise_type") or "")
        if column == 2:
            return int(record.get("caught_apples") or 0)
        if column == 3:
            return self._history_success(record)
        if column == 4:
            return str(record.get("background") or "")
        if column == 5:
            return float(record.get("total_score") or 0)
        return 0

    def _sort_history_records(self, records):
        if self._history_sort_column is None:
            return list(records)
        return sorted(
            records,
            key=self._history_sort_key,
            reverse=bool(self._history_sort_desc),
        )

    def _on_history_header_clicked(self, column):
        if self._history_sort_column == column:
            self._history_sort_desc = not self._history_sort_desc
        else:
            self._history_sort_column = column
            self._history_sort_desc = True
        header = self.ui.tableWidget.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(
            column,
            Qt.DescendingOrder if self._history_sort_desc else Qt.AscendingOrder,
        )
        self._refresh_history_view()

    def _fill_history_table(self, records):
        table = self.ui.tableWidget
        table.clearSpans()
        if not records:
            table.setRowCount(1)
            empty = QtWidgets.QTableWidgetItem("Нет данных за выбранный период")
            empty.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, empty)
            table.setSpan(0, 0, 1, table.columnCount())
            return

        table.setRowCount(len(records))
        for row, record in enumerate(records):
            moment = self._history_date(record)
            date_str = moment.strftime("%d.%m.%Y %H:%M") if moment else "Н/Д"
            total = record.get("total_apples") or 0
            caught = record.get("caught_apples") or 0
            success = self._history_success(record)
            values = [
                date_str,
                record.get("exercise_type", "Упражнение"),
                f"{caught}/{total}",
                f"{success:.0f}%",
                str(record.get("background") or "—"),
                f"{float(record.get('total_score') or 0):.0f}",
            ]
            for column, text in enumerate(values):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if column == 3:
                    if success >= 80:
                        item.setBackground(QtGui.QColor(232, 248, 247))
                    elif success < 50:
                        item.setBackground(QtGui.QColor(253, 244, 244))
                table.setItem(row, column, item)
            table.setRowHeight(row, 40)

    def load_history(self):
        """Загрузка истории тренировок для текущего пользователя из БД"""
        try:
            if self.db is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    "База данных недоступна",
                    "Не удалось подключиться к базе данных.",
                )
                return

            if not self.current_user_id:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Пользователь не выбран",
                    "Пожалуйста, выберите пользователя из списка на главной странице.",
                )
                self.open_main_page()
                return

            self._history_records = self.db.get_exercise_history_by_user(
                self.current_user_id, limit=300
            )
            self.ui.label_history_user.setText(self._current_user_name() or "Не выбран")
            self._refresh_history_view()
        except Exception as e:
            print(f"❌ Ошибка при загрузке истории: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка загрузки",
                f"Не удалось загрузить историю тренировок:\n{str(e)}",
            )

if __name__ == "__main__":
    import qt_bootstrap  # noqa: F401
    setup_runtime()
    app = QtWidgets.QApplication(sys.argv)
    load_styles(app)

    try:
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске приложения: {e}")
        traceback.print_exc()
        sys.exit(1)