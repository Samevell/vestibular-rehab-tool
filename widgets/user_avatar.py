from pathlib import Path

from PyQt5.QtWidgets import QLabel
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QImage, QPainter, QColor, QPixmap, QPainterPath, QBrush
from PyQt5.QtCore import QPointF, QRectF, pyqtProperty, Qt

from app_paths import resolve_asset


class UserAvatar(QLabel):
    """Круглый аватар: фото пользователя или стандартная иконка."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svg_file = ""
        self._renderer = None
        self._photo = None
        self._photo_path = ""
        self._main_color = QColor("#1dbeb7")
        self._circle_color = QColor("#e8f8f7")
        self.setText("")
        self.setAlignment(Qt.AlignCenter)

    def getSvgFile(self):
        return self._svg_file

    def setSvgFile(self, path):
        self._svg_file = path or ""
        resolved = resolve_asset(path) if path else ""
        self._renderer = QSvgRenderer(resolved) if resolved else None
        self.update()

    svg_file = pyqtProperty(str, fget=getSvgFile, fset=setSvgFile)

    def getMainColor(self):
        return self._main_color.name()

    def setMainColor(self, color):
        self._main_color = QColor(color)
        self.update()

    main_color = pyqtProperty(str, fget=getMainColor, fset=setMainColor)

    def getCircleColor(self):
        return self._circle_color.name()

    def setCircleColor(self, color):
        self._circle_color = QColor(color)
        self.update()

    circle_color = pyqtProperty(str, fget=getCircleColor, fset=setCircleColor)

    def setPhotoPath(self, path):
        self._photo_path = path or ""
        if path and Path(path).exists():
            self._photo = QPixmap(path)
        else:
            self._photo = None
        self.update()

    def clearPhoto(self):
        self.setPhotoPath("")

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        circle_size = min(w, h) * 0.92
        cx = (w - circle_size) / 2
        cy = (h - circle_size) / 2
        rect = QRectF(cx, cy, circle_size, circle_size)

        if self._photo and not self._photo.isNull():
            path = QPainterPath()
            path.addEllipse(rect)
            painter.setClipPath(path)
            scaled = self._photo.scaled(
                int(circle_size),
                int(circle_size),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = cx - (scaled.width() - circle_size) / 2
            y = cy - (scaled.height() - circle_size) / 2
            painter.drawPixmap(int(x), int(y), scaled)
            painter.setClipping(False)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QColor("#D7EEEC"))
            painter.drawEllipse(rect.adjusted(0.5, 0.5, -0.5, -0.5))
            painter.end()
            return

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._circle_color))
        painter.drawEllipse(rect)

        if self._renderer and self._renderer.isValid():
            svg_size = self._renderer.defaultSize()
            if not svg_size.isValid():
                svg_size = self.size()
            sw, sh = svg_size.width(), svg_size.height()
            scale = min(circle_size / sw, circle_size / sh) * 0.55
            new_w = max(1, int(sw * scale))
            new_h = max(1, int(sh * scale))
            img = QImage(new_w, new_h, QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.transparent)
            img_painter = QPainter(img)
            img_painter.setRenderHint(QPainter.Antialiasing)
            self._renderer.render(img_painter)
            img_painter.end()
            tint = QPainter(img)
            tint.setCompositionMode(QPainter.CompositionMode_SourceIn)
            tint.fillRect(img.rect(), self._main_color)
            tint.end()
            painter.drawImage(
                QPointF(cx + (circle_size - new_w) / 2, cy + (circle_size - new_h) / 2),
                img,
            )
        painter.end()
