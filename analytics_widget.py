"""Виджет аналитики: вкладки для врача и пациента."""

import matplotlib

matplotlib.use("Qt5Agg")

from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from analytics_plots import build_success_figure
from metrics import aggregate
from rehab_config import TARGET_SUCCESS_MAX, TARGET_SUCCESS_MIN
from session_quality import exclude_reason_label


class AnalyticsWidget(QtWidgets.QWidget):
    """Аналитика упражнения 1: график, таблица (врач), краткая сводка (пациент)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = None
        self._user_id = None
        self._figure = None
        self._canvas = None
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Упражнение:"))
        self.exercise_combo = QtWidgets.QComboBox()
        self.exercise_combo.addItem("Упражнение 1", 1)
        self.exercise_combo.setEnabled(False)
        top.addWidget(self.exercise_combo)
        top.addStretch()
        layout.addLayout(top)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # --- Врач ---
        clinician = QtWidgets.QWidget()
        clinician_layout = QtWidgets.QVBoxLayout(clinician)

        self.clinician_summary = QtWidgets.QLabel()
        self.clinician_summary.setWordWrap(True)
        clinician_layout.addWidget(self.clinician_summary)

        self.canvas_host = QtWidgets.QWidget()
        self.canvas_layout = QtWidgets.QVBoxLayout(self.canvas_host)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        clinician_layout.addWidget(self.canvas_host, stretch=2)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [
                "Дата",
                "Яблок / сек",
                "Поймано",
                "Успешность",
                "Учтена",
                "Причина исключения",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        clinician_layout.addWidget(self.table, stretch=2)

        self.tabs.addTab(clinician, "Для врача")

        # --- Пациент ---
        patient = QtWidgets.QWidget()
        patient_layout = QtWidgets.QVBoxLayout(patient)

        self.patient_canvas_host = QtWidgets.QWidget()
        self.patient_canvas_layout = QtWidgets.QVBoxLayout(self.patient_canvas_host)
        self.patient_canvas_layout.setContentsMargins(0, 0, 0, 0)
        patient_layout.addWidget(self.patient_canvas_host, stretch=3)

        self.patient_text = QtWidgets.QLabel()
        self.patient_text.setWordWrap(True)
        self.patient_text.setAlignment(QtCore.Qt.AlignCenter)
        font = self.patient_text.font()
        font.setPointSize(11)
        self.patient_text.setFont(font)
        patient_layout.addWidget(self.patient_text)

        self.tabs.addTab(patient, "Для пациента")

    def set_database(self, db):
        self._db = db

    def load_user(self, user_id):
        """Загрузить и отобразить аналитику для user_id."""
        self._user_id = user_id
        if self._db is None or user_id is None:
            self._show_empty("База данных или пользователь не выбраны")
            return

        data = aggregate(self._db, user_id, exercise=1)
        sessions = data["sessions"]
        self._refresh_clinician(data, sessions)
        self._refresh_patient(data, sessions)

    def _clear_canvas(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _set_figure(self, layout, sessions):
        self._clear_canvas(layout)
        self._figure = build_success_figure(sessions)
        canvas = FigureCanvas(self._figure)
        canvas.setMinimumHeight(220)
        layout.addWidget(canvas)
        return canvas

    def _show_empty(self, message):
        self.clinician_summary.setText(message)
        self.patient_text.setText(message)
        self.table.setRowCount(0)
        self._clear_canvas(self.canvas_layout)
        self._clear_canvas(self.patient_canvas_layout)

    def _refresh_clinician(self, data, sessions):
        ewma = data.get("ewma")
        trend = data.get("trend", "—")
        band = data.get("in_target_band", {})
        valid_n = data.get("valid_count", 0)
        total_n = len(sessions)

        ewma_txt = f"{int(round(ewma * 100))}%" if ewma is not None else "—"
        band_txt = (
            f"{band.get('count', 0)} из {band.get('total', 0)} "
            f"({int(round(band.get('pct', 0) * 100))}%)"
            if band.get("total")
            else "—"
        )

        self.clinician_summary.setText(
            f"Сессий: {total_n} (учтено: {valid_n}) · "
            f"EWMA: {ewma_txt} · Тренд: {trend} · "
            f"В коридоре {int(TARGET_SUCCESS_MIN * 100)}–{int(TARGET_SUCCESS_MAX * 100)}%: {band_txt}"
        )

        self._canvas = self._set_figure(self.canvas_layout, sessions)
        self._fill_table(sessions)

    def _fill_table(self, sessions):
        self.table.setRowCount(len(sessions))
        for row, s in enumerate(reversed(sessions)):
            rec = s["record"]
            dt = rec.get("exercise_date")
            if dt and hasattr(dt, "strftime"):
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            else:
                date_str = str(dt) if dt else "—"

            params = f"{rec.get('apples_count', '—')} / {rec.get('seconds_per_apple', '—')} с"
            caught = rec.get("caught_apples", 0)
            pct = f"{s['success'] * 100:.1f}%"
            accounted = "Да" if s["is_valid"] else "Нет"
            reason = exclude_reason_label(s["exclude_reason"]) if not s["is_valid"] else ""

            items = [date_str, params, str(caught), pct, accounted, reason]
            for col, text in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                if not s["is_valid"]:
                    item.setBackground(QtGui.QColor(220, 220, 220))
                self.table.setItem(row, col, item)

    def _refresh_patient(self, data, sessions):
        self._set_figure(self.patient_canvas_layout, sessions)

        ewma = data.get("ewma")
        trend = data.get("trend", "стабильно")
        if ewma is None:
            self.patient_text.setText(
                "Пока мало данных для оценки прогресса. Продолжайте тренировки."
            )
            return

        pct = int(round(ewma * 100))
        corridor_lo = int(TARGET_SUCCESS_MIN * 100)
        corridor_hi = int(TARGET_SUCCESS_MAX * 100)

        if TARGET_SUCCESS_MIN <= ewma <= TARGET_SUCCESS_MAX:
            zone = "в целевом диапазоне"
        elif ewma < TARGET_SUCCESS_MIN:
            zone = "ниже целевого диапазона — нагрузку можно упростить"
        else:
            zone = "выше целевого диапазона — нагрузку можно постепенно увеличивать"

        self.patient_text.setText(
            f"Ваш средний результат по последним тренировкам — около {pct}%. "
            f"Целевой коридор: {corridor_lo}–{corridor_hi}%. "
            f"Сейчас показатель {zone}. Тренд: {trend}."
        )
