from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import QPainter, QPixmap


class ExampleImage(QWidget):
    """Превью упражнения: рисует исходник с сохранением пропорций по размеру виджета."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = QPixmap()
        self._scaled = QPixmap()
        self.setMinimumSize(240, 140)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        policy.setVerticalStretch(1)
        self.setSizePolicy(policy)

    def setSource(self, pixmap):
        self._source = pixmap if pixmap is not None else QPixmap()
        self._scaled = QPixmap()
        self.update()

    def setPixmap(self, pixmap):
        self.setSource(pixmap)

    def sizeHint(self):
        return QSize(480, 270)

    def resizeEvent(self, event):
        self._scaled = QPixmap()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._source.isNull() or self.width() < 2 or self.height() < 2:
            return
        scaled = self._scaled_pixmap()
        if scaled.isNull():
            return
        ratio = scaled.devicePixelRatio() or 1.0
        draw_w = scaled.width() / ratio
        draw_h = scaled.height() / ratio
        x = (self.width() - draw_w) / 2
        y = (self.height() - draw_h) / 2
        painter.drawPixmap(QRect(int(x), int(y), int(draw_w), int(draw_h)), scaled)

    def _scaled_pixmap(self):
        if not self._scaled.isNull():
            return self._scaled
        ratio = self.devicePixelRatioF() or 1.0
        target = QSize(
            max(1, int(self.width() * ratio)),
            max(1, int(self.height() * ratio)),
        )
        scaled = self._source.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(ratio)
        self._scaled = scaled
        return scaled
