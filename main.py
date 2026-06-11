import sys
import traceback
from PyQt5 import QtWidgets
from window_ui import Ui_MainWindow
from detect_thread import CameraThread
from ex_2 import CameraThread2
from ex_3 import CameraThread3
# Импортируем заглушки для упражнений 4-9
from ex_4 import CameraThread4
from ex_5 import CameraThread5
from ex_6 import CameraThread6
from ex_7 import CameraThread7
from ex_8 import CameraThread8
from ex_9 import CameraThread9
from PyQt5.QtGui import QImage, QPixmap
import cv2
from PyQt5.QtCore import Qt, QTimer, QSize, QSize
from PyQt5.QtCore import QSettings
from PyQt5 import QtGui
from widgets.clickable_card import ClickableCard
from style_loader import load_styles
from analytics.recommend import recommend
from analytics.ui_binding import (
    apply_exercise_params,
    exercise_id_from_key,
    load_dict_to_ui_params,
    read_exercise_params,
)

# Импортируем БД с предварительным подключением
try:
    from database_preconnected import DatabasePreconnected as Database
    print("✅ Используется DatabasePreconnected")
except ImportError as e:
    print(f"❌ Не удалось импортировать database_preconnected: {e}")
    # Резервный вариант - обычная БД
    try:
        from database_sync import DatabaseSync as Database
        print("✅ Используется DatabaseSync (резервный вариант)")
    except ImportError:
        print("❌ Нет доступных модулей БД")
        Database = None

# Перехватчик исключений
def exception_hook(exctype, value, traceback_obj):
    """Перехват исключений для отображения в консоли"""
    print(f"🚨 Критическая ошибка: {exctype.__name__}: {value}")
    traceback.print_exception(exctype, value, traceback_obj)
    
    # Показываем сообщение об ошибке
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
            if Database:
                self.db = Database()
            else:
                self.db = None
                print("⚠️ База данных недоступна")
            
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
            self.ui.tableWidget.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Stretch
            )
            self.ui.tableWidget.setStyleSheet("""
            QTableWidget {
                background: white;
                border-radius: 10px;
            }

            QHeaderView::section {
                background-color: #14d4c7;
                color: white;
                padding: 5px;
                border: none;
            }

            QTableWidget::item {
                padding: 5px;
            }
            """)
            self.ui.tableWidget.setEditTriggers(
                QtWidgets.QAbstractItemView.NoEditTriggers
            )
            
            # Проверяем состояние БД
            if self.db and hasattr(self.db, 'is_connected') and not self.db.is_connected:
                print("⚠️ Нет подключения к БД. Проверьте:")
                print("   1. Запущен ли MySQL сервер")
                print("   2. Правильный ли пароль ")
                print("   3. Существует ли база 'trainer'")
                print("   4. Доступен ли сервер на 127.0.0.1:3306")
            
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
            self.ui.card_exit_btn.clicked.connect(self.close)
            self.ui.pushButton.clicked.connect(self.save_user_settings)
            self.ui.btn_back_settings.clicked.connect(
                lambda: self.ui.stacked_widget_main.setCurrentIndex(0)
            )
            self.ui.btn_delete_user.clicked.connect(self.delete_selected_user)
            
            # Подключаем изменение выбора в комбобоксе
            self.ui.comboBox_choose_user.currentIndexChanged.connect(self.on_user_selected)
            
            # Настраиваем таблицу истории
            self.setup_history_table()
            self.setup_recommendation_buttons()
            
            self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_main)
            self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_emty)

            # Загружаем пользователей в комбобокс
            self.load_users()
            
            # Загружаем изображения
            print("🔄 Загрузка изображений...")
            try:
                self.original_pixmap = QPixmap("./img/eex1.png")
                self.ui.lable_apple_example_img.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img.setScaledContents(False)
                
                self.original_pixmap_ex2 = QPixmap("./img/eex2.png")
                self.ui.lable_apple_example_img_2.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_2.setScaledContents(False)

                self.original_pixmap_ex3 = QPixmap("./img/eex3.png")
                self.ui.lable_apple_example_img_3.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_3.setScaledContents(False)
                
                # Заглушки для изображений упражнений 4-9
                self.original_pixmap_ex4 = QPixmap("./img/eex4.png") if QPixmap("./img/eex4.png") else QPixmap()
                self.ui.lable_apple_example_img_4.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_4.setScaledContents(False)
                self.original_pixmap_ex5 = QPixmap("./img/eex5.png") if QPixmap("./img/eex5.png") else QPixmap()
                self.ui.lable_apple_example_img_5.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_5.setScaledContents(False)
                self.original_pixmap_ex6 = QPixmap("./img/eex6.png") if QPixmap("./img/eex6.png") else QPixmap()
                self.ui.lable_apple_example_img_6.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_6.setScaledContents(False)
                self.original_pixmap_ex7 = QPixmap("./img/eex7.png") if QPixmap("./img/eex7.png") else QPixmap()
                self.ui.lable_apple_example_img_7.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_7.setScaledContents(False)
                self.original_pixmap_ex8 = QPixmap("./img/eex8.png") if QPixmap("./img/eex8.png") else QPixmap()
                self.ui.lable_apple_example_img_8.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_8.setScaledContents(False)
                self.original_pixmap_ex9 = QPixmap("./img/eex9.png") if QPixmap("./img/eex9.png") else QPixmap()
                self.ui.lable_apple_example_img_9.setAlignment(Qt.AlignCenter)
                self.ui.lable_apple_example_img_9.setScaledContents(False)
                
            except Exception as e:
                print(f"⚠️ Ошибка загрузки изображений: {e}")
            
            # Устанавливаем начальные значения
            self.ui.spinBox_apple_count.setValue(12)
            self.ui.spinBox_apple_second.setValue(10)
            self.ui.spinBox_apple_count_2.setValue(5)
            self.ui.spinBox_apple_second_2.setValue(4)
            self.ui.spinBox_apple_count_3.setValue(5)
            
            # Переменные для хранения результатов упражнений
            self.exercise_score = 0
            self.exercise_type = None

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
            (self.ui.btn_save_baseline, "./img/bookmark_icon.svg"),
            (self.ui.btn_apply_recommendation, "./img/sparkles_icon.svg"),
            (self.ui.btn_restore_baseline, "./img/reset_icon.svg"),
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
        """Настройка таблицы истории тренировок (БЕЗ ID)"""
        # Устанавливаем заголовки столбцов
        headers = [
            "Упражнение",
            "Дата и время",
            "Всего яблок",
            "Поймано",
            "Успешность",
            "Сложность",
            "Фон",
            "Коэффициент",
            "Балл"
        ]
        
        self.ui.tableWidget.setColumnCount(len(headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)
        
        # Настройка ширины столбцов
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)
        
        # Настройка выравнивания заголовков
        for i in range(len(headers)):
            self.ui.tableWidget.horizontalHeaderItem(i).setTextAlignment(Qt.AlignCenter)
        
        # Настройка ширины столбцов
        self.ui.tableWidget.setColumnWidth(0, 120)  # Упражнение
        self.ui.tableWidget.setColumnWidth(1, 150)  # Дата и время
        self.ui.tableWidget.setColumnWidth(2, 150)  # Пользователь
        self.ui.tableWidget.setColumnWidth(3, 100)  # Всего яблок
        self.ui.tableWidget.setColumnWidth(4, 100)  # Поймано
        self.ui.tableWidget.setColumnWidth(5, 100)  # Успешность
        self.ui.tableWidget.setColumnWidth(6, 100)  # Сложность
        self.ui.tableWidget.setColumnWidth(7, 100)  # Фон
        self.ui.tableWidget.setColumnWidth(8, 100)  # Коэффициент

    def load_users(self):
        """Загрузка списка пользователей в комбобокс"""
        if self.db is None:
            return
        
        self.ui.comboBox_choose_user.clear()
        
        # Добавляем опцию "Выберите пользователя"
        self.ui.comboBox_choose_user.addItem("-- Выберите пользователя --", None)
        
        users = self.db.get_all_users()
        
        for user in users:
            text = f"{user['first_name']} {user['last_name']}"
            self.ui.comboBox_choose_user.addItem(text, user['id'])
        
        # Восстанавливаем выбранного пользователя
        if self.current_user_id:
            index = self.ui.comboBox_choose_user.findData(self.current_user_id)
            if index > 0:  # не выбираем "-- Выберите пользователя --"
                self.ui.comboBox_choose_user.setCurrentIndex(index)
                user_name = self.ui.comboBox_choose_user.currentText()
                self.ui.label_16.setText(f"Пользователь: {user_name}")
    
    def on_user_selected(self, index):
        """Обработка выбора пользователя из комбобокса"""
        user_id = self.ui.comboBox_choose_user.currentData()
        
        if user_id:
            self.current_user_id = user_id
            self.settings.setValue("current_user_id", user_id)
            
            user_name = self.ui.comboBox_choose_user.currentText()
            print(f"👤 Выбран пользователь: {user_name} (ID={user_id})")
            self.ui.label_16.setText(f"Пользователь: {user_name}")
        else:
            # Пользователь не выбран (выбрана опция "-- Выберите пользователя --")
            self.current_user_id = None
            self.settings.setValue("current_user_id", None)
            self.ui.label_16.setText("Пользователь: не выбран")

    def delete_selected_user(self):
        """Удаление выбранного пользователя"""
        user_id = self.ui.comboBox_choose_user.currentData()
        
        if not user_id:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите пользователя для удаления")
            return
        
        user_name = self.ui.comboBox_choose_user.currentText()
        
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
            self.ui.label_16.setText("Пользователь: не выбран")
        
        # Перезагружаем комбобокс
        self.load_users()
        
        QtWidgets.QMessageBox.information(self, "Успех", f"Пользователь {user_name} удален")

    def on_button_clicked(self, button):
        for btn in self.ui.buttonGroup.buttons():
            btn.setStyleSheet("")  # сбрасываем стиль
        button.setStyleSheet("background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #cfa8ff,stop: 1 #8e6ecb);")

    def save_user_settings(self):
        """Сохранение пользователя и переход в главное меню"""
        print("🔄 Нажата кнопка 'Сохранить'")
        
        try:
            if self.db is None:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "База данных недоступна!")
                return
                
            first_name = self.ui.lineEdit_UserName.text().strip()
            last_name = self.ui.lineEdit_UserLastName.text().strip()
            
            print(f"📝 Введенные данные: {first_name} {last_name}")
            
            if not first_name or not last_name:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя и фамилию!")
                return
            
            # Отключаем кнопку на время операции
            self.ui.pushButton.setEnabled(False)
            self.ui.pushButton.setText("Сохранение...")
            
            # Показываем сообщение о сохранении
            saving_msg = QtWidgets.QMessageBox()
            saving_msg.setWindowTitle("Сохранение")
            saving_msg.setText("Сохранение пользователя...")
            saving_msg.setStandardButtons(QtWidgets.QMessageBox.NoButton)
            saving_msg.show()
            
            # Обновляем UI
            QtWidgets.QApplication.processEvents()
            
            # Синхронное сохранение пользователя
            try:
                user_id = self.db.get_or_create_user(first_name, last_name)
            except Exception as e:
                user_id = None
                print(f"❌ Исключение при сохранении пользователя: {e}")
            
            # Закрываем сообщение
            saving_msg.close()
            
            # Восстанавливаем кнопку
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton.setText("Сохранить")
            
            if user_id is None:
                QtWidgets.QMessageBox.warning(
                    self, 
                    "Ошибка", 
                    "Не удалось сохранить пользователя. Проверьте подключение к базе данных."
                )
                return
            
            self.current_user_id = user_id
            self.settings.setValue("current_user_id", user_id)
            
            # Очищаем поля
            self.ui.lineEdit_UserName.clear()
            self.ui.lineEdit_UserLastName.clear()
            
            # Перезагружаем пользователей в комбобокс
            self.load_users()
            
            # Обновляем label с именем пользователя
            self.ui.label_16.setText(f"Пользователь: {first_name} {last_name}")
            
            # Переходим в главное меню
            self.open_main_page()
            
            QtWidgets.QMessageBox.information(
                self, 
                "Успех", 
                f"Данные сохранены!\nПользователь: {first_name} {last_name}\nID: {user_id}"
            )
            
            print("✅ Пользователь успешно сохранен")
            
        except Exception as e:
            print(f"❌ Ошибка в save_user_settings: {e}")
            traceback.print_exc()
            
            # Восстанавливаем кнопку в любом случае
            self.ui.pushButton.setEnabled(True)
            self.ui.pushButton.setText("Сохранить")
            
            QtWidgets.QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Произошла ошибка:\n{str(e)}"
            )
    
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
    
    def calculate_coefficient_ex6(self, objects_count, bg_speed, caught_objects):
        """Расчет коэффициента для упражнения 6"""
        if objects_count == 0:
            return 0
        
        success_rate = caught_objects / objects_count
        
        # Коэффициент скорости фона
        bg_multipliers = {
            'Выкл': 1.0,
            'Медленно': 1.2,
            'Средне': 1.5,
            'Быстро': 2.0
        }
        
        bg_factor = bg_multipliers.get(bg_speed, 1.0)
        coefficient = success_rate * bg_factor
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
        
        self.exercise_score = 0
        
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
    
    def open_page_settings(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_settings)

    def open_main_page(self):
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page_main)
    
    # ==================== Отображение описаний упражнений ====================
    
    def show_apple_ex_description(self):
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_apples)
        self.update_static_image()
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

    def update_static_image(self):
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.ui.lable_apple_example_img.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img.setPixmap(scaled_pixmap)

        if self.original_pixmap_ex2:
            scaled_pixmap_ex2 = self.original_pixmap_ex2.scaled(
                self.ui.lable_apple_example_img_2.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_2.setPixmap(scaled_pixmap_ex2)

        if self.original_pixmap_ex3:
            scaled_pixmap_ex3 = self.original_pixmap_ex3.scaled(
                self.ui.lable_apple_example_img_3.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_3.setPixmap(scaled_pixmap_ex3)
        
        # Обновление изображений для упражнений 4-9
        if hasattr(self, 'original_pixmap_ex4') and self.original_pixmap_ex4:
            scaled = self.original_pixmap_ex4.scaled(
                self.ui.lable_apple_example_img_4.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_4.setPixmap(scaled)
        
        if hasattr(self, 'original_pixmap_ex5') and self.original_pixmap_ex5:
            scaled = self.original_pixmap_ex5.scaled(
                self.ui.lable_apple_example_img_5.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_5.setPixmap(scaled)
        
        if hasattr(self, 'original_pixmap_ex6') and self.original_pixmap_ex6:
            scaled = self.original_pixmap_ex6.scaled(
                self.ui.lable_apple_example_img_6.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_6.setPixmap(scaled)
        
        if hasattr(self, 'original_pixmap_ex7') and self.original_pixmap_ex7:
            scaled = self.original_pixmap_ex7.scaled(
                self.ui.lable_apple_example_img_7.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_7.setPixmap(scaled)
        
        if hasattr(self, 'original_pixmap_ex8') and self.original_pixmap_ex8:
            scaled = self.original_pixmap_ex8.scaled(
                self.ui.lable_apple_example_img_8.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_8.setPixmap(scaled)
        
        if hasattr(self, 'original_pixmap_ex9') and self.original_pixmap_ex9:
            scaled = self.original_pixmap_ex9.scaled(
                self.ui.lable_apple_example_img_9.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.ui.lable_apple_example_img_9.setPixmap(scaled)

    def resizeEvent(self, event):
        self.update_static_image()
        super().resizeEvent(event)

    def update_frame(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        q_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.ui.label_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.ui.label_video.setPixmap(scaled_pixmap)
        self.ui.label_video.setAlignment(Qt.AlignCenter)

    def closeEvent(self, event):
        """Закрытие соединения с БД при выходе"""
        if self.db:
            self.db.close()
        event.accept()
        
    def stop_camera(self):
        if hasattr(self, 'thread'):
            self.thread.stop()
            self.thread.wait()
        self.open_page_choose_ex()
        self.current_exercise = None
        self.ui.stacked_widget_ex_choose.setCurrentWidget(self.ui.page_emty)

    def open_history_page(self):
        """Открытие страницы истории тренировок"""
        self.ui.stacked_widget_main.setCurrentWidget(self.ui.page)
        self.load_history()
    
    def load_history(self):
        """Загрузка истории тренировок для текущего пользователя из БД"""
        try:
            if self.db is None:
                print("❌ База данных недоступна для загрузки истории")
                QtWidgets.QMessageBox.warning(
                    self,
                    "База данных недоступна",
                    "Не удалось подключиться к базе данных."
                )
                return
            
            if not self.current_user_id:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Пользователь не выбран",
                    "Пожалуйста, выберите пользователя из списка на главной странице."
                )
                self.open_main_page()
                return
            
            print("🔄 Загрузка истории тренировок...")
            
            self.ui.tableWidget.setRowCount(0)
            records = self.db.get_exercise_history_by_user(self.current_user_id, limit=100)
            
            print(f"✅ Загружено записей истории: {len(records)}")
            
            if len(records) == 0:
                self.ui.tableWidget.setRowCount(1)
                no_data_item = QtWidgets.QTableWidgetItem("Нет данных о тренировках")
                no_data_item.setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.setItem(0, 0, no_data_item)
                self.ui.tableWidget.setSpan(0, 0, 1, self.ui.tableWidget.columnCount())
                return
            
            self.ui.tableWidget.setRowCount(len(records))
            
            for row, record in enumerate(records):
                exercise_type = record.get('exercise_type', 'Неизвестно')
                self.ui.tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(exercise_type))
                
                exercise_date = record.get('exercise_date')
                if exercise_date:
                    if hasattr(exercise_date, 'strftime'):
                        date_str = exercise_date.strftime("%d.%m.%Y %H:%M")
                    else:
                        date_str = str(exercise_date)
                else:
                    date_str = "Н/Д"
                date_item = QtWidgets.QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.setItem(row, 1, date_item)
                
                total_apples = record.get('total_apples', 0)
                total_item = QtWidgets.QTableWidgetItem(str(total_apples))
                total_item.setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.setItem(row, 2, total_item)
                
                caught_apples = record.get('caught_apples', 0)
                caught_item = QtWidgets.QTableWidgetItem(str(caught_apples))
                caught_item.setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.setItem(row, 3, caught_item)
                
                if total_apples > 0:
                    success_rate = (caught_apples / total_apples) * 100
                    success_text = f"{success_rate:.1f}%"
                else:
                    success_text = "0%"
                success_item = QtWidgets.QTableWidgetItem(success_text)
                success_item.setTextAlignment(Qt.AlignCenter)
                if total_apples > 0:
                    success_rate_val = caught_apples / total_apples
                    if success_rate_val >= 0.8:
                        success_item.setBackground(QtGui.QColor(200, 255, 200))
                    elif success_rate_val >= 0.5:
                        success_item.setBackground(QtGui.QColor(255, 255, 200))
                    else:
                        success_item.setBackground(QtGui.QColor(255, 200, 200))
                self.ui.tableWidget.setItem(row, 4, success_item)
                
                difficulty = record.get('difficulty', '')
                difficulty_item = QtWidgets.QTableWidgetItem(str(difficulty))
                difficulty_item.setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.setItem(row, 5, difficulty_item)
                
                background = record.get('background', '')
                background_item = QtWidgets.QTableWidgetItem(str(background))
                background_item.setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.setItem(row, 6, background_item)
                
                coefficient = record.get('coefficient', 0)
                coeff_item = QtWidgets.QTableWidgetItem(f"{coefficient:.2f}")
                coeff_item.setTextAlignment(Qt.AlignCenter)
                if coefficient >= 1.5:
                    coeff_item.setBackground(QtGui.QColor(200, 255, 200))
                elif coefficient >= 1.0:
                    coeff_item.setBackground(QtGui.QColor(255, 255, 200))
                else:
                    coeff_item.setBackground(QtGui.QColor(255, 200, 200))
                self.ui.tableWidget.setItem(row, 7, coeff_item)
                
                total_score = record.get('total_score', 0)
                score_item = QtWidgets.QTableWidgetItem(f"{total_score:.2f}")
                score_item.setTextAlignment(Qt.AlignCenter)
                max_score = total_apples * 10
                if max_score > 0:
                    score_percent = (total_score / max_score) * 100
                    if score_percent >= 80:
                        score_item.setBackground(QtGui.QColor(200, 255, 200))
                    elif score_percent >= 50:
                        score_item.setBackground(QtGui.QColor(255, 255, 200))
                    else:
                        score_item.setBackground(QtGui.QColor(255, 200, 200))
                self.ui.tableWidget.setItem(row, 8, score_item)
            
            current_user_name = self.ui.comboBox_choose_user.currentText()
            if current_user_name == "-- Выберите пользователя --":
                current_user_name = "Не выбран"
            self.ui.label_17.setText(f"История тренировок - {current_user_name}")
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке истории: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка загрузки",
                f"Не удалось загрузить историю тренировок:\n{str(e)}"
            )

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    load_styles(app)

    try:
        window = MainWindow()
        window.setWindowTitle("Тренажер вестибулярного аппарата")
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске приложения: {e}")
        traceback.print_exc()
        sys.exit(1)