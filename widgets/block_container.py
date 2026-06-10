from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QBrush, QPainterPath


class BlockContainer(QFrame):
    def __init__(
        self,
        parent=None,
        bg_color="#ffffff",
        radius=20,
        shadow_color="#000000",
        shadow_alpha=30,
        shadow_blur=40
    ):
        super().__init__(parent)

        self.setAttribute(Qt.WA_TranslucentBackground)

        self._bg_color = QColor(bg_color)
        self._radius = radius

        # --- только визуальная тень ---
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(shadow_blur)
        shadow.setOffset(0, 0)  # важно: не влияет на позицию
        color = QColor(shadow_color)
        color.setAlpha(shadow_alpha)
        shadow.setColor(color)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())

        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawPath(path)