from PyQt5.QtCore import QDate, QEvent, QLocale, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QTextCharFormat
from PyQt5.QtWidgets import (
    QCalendarWidget,
    QLabel,
    QPushButton,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class HistoryCalendar(QCalendarWidget):
    """Клики по дням соседнего месяца выбирают дату, но не меняют страницу."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_before_click = None
        self._allow_page_change = True
        self.currentPageChanged.connect(self._keep_page_on_date_click)
        self._install_filters()

    def showEvent(self, event):
        super().showEvent(event)
        self._install_filters()

    def _install_filters(self):
        view = self.findChild(QTableView)
        if view is not None:
            view.viewport().installEventFilter(self)
        for button in self.findChildren(QToolButton):
            button.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if isinstance(obj, QToolButton):
                self._allow_page_change = True
            elif obj.parent() is not None and isinstance(obj.parent(), QTableView):
                self._allow_page_change = False
                self._page_before_click = (self.yearShown(), self.monthShown())
        return super().eventFilter(obj, event)

    def _keep_page_on_date_click(self, year, month):
        if self._allow_page_change or self._page_before_click is None:
            return
        shown_year, shown_month = self._page_before_click
        if year == shown_year and month == shown_month:
            return
        self.blockSignals(True)
        self.setCurrentPage(shown_year, shown_month)
        self.blockSignals(False)


class HistoryPeriodPopup(QWidget):
    periodChanged = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("popup_history_period")
        self._applied_start = None
        self._applied_end = None
        self._draft_start = None
        self._marked = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.hint = QLabel("Выберите начало и конец периода")
        self.hint.setObjectName("label_history_period_hint")
        self.hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint)

        self.calendar = HistoryCalendar()
        self.calendar.setObjectName("calendar_history_period")
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.calendar.setLocale(QLocale(QLocale.Russian, QLocale.Russia))
        self.calendar.setMaximumDate(QDate.currentDate())
        self.calendar.setFixedSize(292, 220)
        self.calendar.clicked.connect(self._on_date_clicked)
        layout.addWidget(self.calendar, 0, Qt.AlignHCenter)

        self.btn_all = QPushButton("За всё время")
        self.btn_all.setObjectName("btn_history_period_all")
        self.btn_all.setCursor(Qt.PointingHandCursor)
        self.btn_all.clicked.connect(self._select_all)
        layout.addWidget(self.btn_all)

        self.setStyleSheet(
            """
            #popup_history_period {
                background: #ffffff;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
            #label_history_period_hint {
                color: #8A97A6;
                background: transparent;
                font-size: 15px;
            }
            #btn_history_period_all {
                background: #E8F8F7;
                color: #1dbeb7;
                border: none;
                border-radius: 12px;
                min-height: 36px;
                font-weight: 600;
            }
            #btn_history_period_all:hover {
                background: #1dbeb7;
                color: #ffffff;
            }
            #calendar_history_period {
                background: #ffffff;
            }
            #calendar_history_period QWidget#qt_calendar_navigationbar {
                background: #1dbeb7;
                border-radius: 10px;
            }
            #calendar_history_period QToolButton {
                color: #ffffff;
                background: transparent;
                font-weight: 600;
            }
            #calendar_history_period QAbstractItemView:enabled {
                selection-background-color: #1dbeb7;
                selection-color: #ffffff;
                outline: none;
            }
            """
        )

    def show_for(self, button, start=None, end=None):
        self._applied_start = start
        self._applied_end = end
        self._draft_start = None
        self._paint_range(start, end)
        if start is not None:
            self.calendar.setSelectedDate(start)
            self.calendar.setCurrentPage(start.year(), start.month())
        else:
            today = QDate.currentDate()
            self.calendar.setSelectedDate(today)
            self.calendar.setCurrentPage(today.year(), today.month())
        self.hint.setText("Выберите начало и конец периода")
        self.adjustSize()
        pos = button.mapToGlobal(button.rect().bottomLeft())
        self.move(pos)
        self.show()
        self.raise_()

    def _format_date(self, date):
        return date.toString("dd.MM.yyyy")

    def _on_date_clicked(self, date):
        if self._draft_start is None:
            self._draft_start = date
            self._paint_range(date, date)
            self.hint.setText(f"Начало: {self._format_date(date)}. Выберите конец")
            return
        start, end = self._draft_start, date
        if end < start:
            start, end = end, start
        self._apply(start, end)

    def _select_all(self):
        self._apply(None, None)

    def _apply(self, start, end):
        self._applied_start = start
        self._applied_end = end
        self._draft_start = None
        self.periodChanged.emit(start, end)
        self.hide()

    def _paint_range(self, start, end):
        empty = QTextCharFormat()
        for date in self._marked:
            self.calendar.setDateTextFormat(date, empty)
        self._marked = []
        if start is None or end is None:
            return
        if end < start:
            start, end = end, start
        mid = QTextCharFormat()
        mid.setBackground(QBrush(QColor("#E8F8F7")))
        mid.setForeground(QBrush(QColor("#2C3E50")))
        ends = QTextCharFormat()
        ends.setBackground(QBrush(QColor("#1dbeb7")))
        ends.setForeground(QBrush(QColor("#ffffff")))
        current = QDate(start)
        while current <= end:
            fmt = ends if current == start or current == end else mid
            self.calendar.setDateTextFormat(current, fmt)
            self._marked.append(QDate(current))
            current = current.addDays(1)
