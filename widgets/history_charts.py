from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QFont, QLinearGradient


TEAL = QColor("#1dbeb7")
TEAL_SOFT = QColor(29, 190, 183, 40)
TEXT = QColor("#2C3E50")
MUTED = QColor("#8A97A6")
GRID = QColor("#E8EEF2")


class HistoryLineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = "Успешность по занятиям"
        self._points = []
        self.setMinimumSize(160, 120)

    def setTitle(self, title):
        self._title = title
        self.update()

    def set_points(self, points):
        self._points = list(points or [])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        font_title = QFont("Segoe UI", 14)
        font_title.setBold(True)
        painter.setFont(font_title)
        painter.setPen(TEXT)
        title_rect = QRectF(16, 10, self.width() - 32, 28)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self._title)

        left_gutter = 58
        right_pad = 18
        bottom_gutter = 32
        plot = QRectF(
            left_gutter,
            title_rect.bottom() + 18,
            max(40.0, self.width() - left_gutter - right_pad),
            max(40.0, self.height() - title_rect.bottom() - 18 - bottom_gutter),
        )
        if plot.width() < 40 or plot.height() < 40:
            return

        painter.setPen(QPen(GRID, 1))
        for i in range(5):
            y = plot.top() + plot.height() * i / 4
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        font_axis = QFont("Segoe UI", 11)
        painter.setFont(font_axis)
        painter.setPen(MUTED)
        for i, label in enumerate(("100%", "75%", "50%", "25%", "0%")):
            y = plot.top() + plot.height() * i / 4
            painter.drawText(
                QRectF(8, y - 10, left_gutter - 14, 20),
                Qt.AlignRight | Qt.AlignVCenter,
                label,
            )

        if len(self._points) < 1:
            painter.setPen(MUTED)
            painter.setFont(QFont("Segoe UI", 13))
            painter.drawText(plot, Qt.AlignCenter, "Пока мало данных")
            return

        values = [max(0.0, min(100.0, float(p[1]))) for p in self._points]
        labels = [str(p[0]) for p in self._points]
        n = len(values)
        x_pad = 10 if n > 1 else plot.width() / 2

        def pt(index, value):
            if n == 1:
                x = plot.left() + plot.width() / 2
            else:
                x = plot.left() + x_pad + (plot.width() - 2 * x_pad) * index / (n - 1)
            y = plot.bottom() - plot.height() * (value / 100.0)
            return QPointF(x, y)

        path = QPainterPath(pt(0, values[0]))
        for i in range(1, n):
            path.lineTo(pt(i, values[i]))

        fill = QPainterPath(path)
        fill.lineTo(QPointF(pt(n - 1, 0).x(), plot.bottom()))
        fill.lineTo(QPointF(pt(0, 0).x(), plot.bottom()))
        fill.closeSubpath()
        gradient = QLinearGradient(plot.topLeft(), plot.bottomLeft())
        gradient.setColorAt(0, QColor(29, 190, 183, 70))
        gradient.setColorAt(1, QColor(29, 190, 183, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(fill)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(TEAL, 2.4))
        painter.drawPath(path)

        painter.setBrush(QBrush(TEAL))
        for i, value in enumerate(values):
            painter.drawEllipse(pt(i, value), 3.2, 3.2)

        ticks = {0, n - 1}
        if n > 2:
            ticks.add(n // 2)
        painter.setPen(MUTED)
        painter.setFont(font_axis)
        for i in sorted(ticks):
            x = pt(i, 0).x()
            if i == 0:
                box = QRectF(plot.left(), plot.bottom() + 6, 64, 20)
                align = Qt.AlignLeft | Qt.AlignTop
            elif i == n - 1:
                box = QRectF(plot.right() - 64, plot.bottom() + 6, 64, 20)
                align = Qt.AlignRight | Qt.AlignTop
            else:
                box = QRectF(x - 40, plot.bottom() + 6, 80, 20)
                align = Qt.AlignHCenter | Qt.AlignTop
            painter.drawText(box, align, labels[i])


class HistoryBarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = "Средний успех по упражнениям"
        self._bars = []
        self.setMinimumSize(160, 120)

    def setTitle(self, title):
        self._title = title
        self.update()

    def set_bars(self, bars):
        self._bars = list(bars or [])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        font_title = QFont("Segoe UI", 14)
        font_title.setBold(True)
        painter.setFont(font_title)
        painter.setPen(TEXT)
        painter.drawText(QRectF(16, 8, self.width() - 32, 34), Qt.AlignLeft | Qt.AlignVCenter, self._title)

        plot = QRectF(16, 50, self.width() - 32, self.height() - 66)
        if not self._bars:
            painter.setPen(MUTED)
            painter.setFont(QFont("Segoe UI", 13))
            painter.drawText(plot, Qt.AlignCenter, "Пока мало данных")
            return

        count = len(self._bars)
        row_h = plot.height() / count
        label_w = 92
        value_w = 52
        bar_left = plot.left() + label_w
        bar_right = plot.right() - value_w
        bar_max = max(8.0, bar_right - bar_left)

        font_row = QFont("Segoe UI", 12)
        painter.setFont(font_row)
        for index, (label, value) in enumerate(self._bars):
            value = max(0.0, min(100.0, float(value)))
            y = plot.top() + index * row_h
            cy = y + row_h / 2
            painter.setPen(TEXT)
            painter.drawText(
                QRectF(plot.left(), y, label_w - 8, row_h),
                Qt.AlignVCenter | Qt.AlignLeft,
                label,
            )
            track = QRectF(bar_left, cy - 7, bar_max, 14)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#F1F5F8")))
            painter.drawRoundedRect(track, 7, 7)
            fill_w = bar_max * (value / 100.0)
            if fill_w > 2:
                painter.setBrush(QBrush(TEAL))
                painter.drawRoundedRect(QRectF(bar_left, cy - 7, fill_w, 14), 7, 7)
            painter.setPen(MUTED)
            painter.drawText(
                QRectF(bar_right, y, value_w, row_h),
                Qt.AlignVCenter | Qt.AlignRight,
                f"{value:.0f}%",
            )
