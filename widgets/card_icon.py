from PyQt5.QtWidgets import QLabel
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QImage, QPainter, QColor
from PyQt5.QtCore import QPointF, QRectF, pyqtProperty, Qt

from app_paths import resolve_asset


class CardIcon(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._svg_file = ""
        self._renderer = None

        self._main_color = QColor("#2ec4b6")
        self._circle_color = QColor("#eaf6f5")
        
        # ДОБАВИТЬ: свойство scale
        self._scale = 1.0  # 1.0 = стандартный размер, можно менять

        self.setText("")
        self.setAlignment(Qt.AlignCenter)

    # ===== ДОБАВИТЬ: СВОЙСТВО SCALE =====
    def getScale(self):
        return self._scale

    def setScale(self, value):
        self._scale = float(value)
        self.update()

    scale = pyqtProperty(float, fget=getScale, fset=setScale)

    # ===== SVG =====
    def getSvgFile(self):
        return self._svg_file

    def setSvgFile(self, path):
        self._svg_file = path
        resolved = resolve_asset(path) if path else ""
        self._renderer = QSvgRenderer(resolved) if resolved else None
        self.update()

    svg_file = pyqtProperty(str, fget=getSvgFile, fset=setSvgFile)

    # ===== MAIN COLOR =====
    def getMainColor(self):
        return self._main_color.name()

    def setMainColor(self, color):
        self._main_color = QColor(color)
        self.update()

    main_color = pyqtProperty(str, fget=getMainColor, fset=setMainColor)

    # ===== CIRCLE COLOR =====
    def getCircleColor(self):
        return self._circle_color.name()

    def setCircleColor(self, color):
        self._circle_color = QColor(color)
        self.update()

    circle_color = pyqtProperty(str, fget=getCircleColor, fset=setCircleColor)

    # ===== PAINT =====
    def paintEvent(self, event):
        if not self._renderer or not self._renderer.isValid():
            return

        w, h = self.width(), self.height()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- круг (с учётом scale) ---
        circle_size = min(w, h) * 0.75 * self._scale  # ИСПРАВЛЕНО: self._scale
        cx = (w - circle_size) / 2
        cy = (h - circle_size) / 2

        painter.setPen(Qt.NoPen)
        painter.setBrush(self._circle_color)
        painter.drawEllipse(QRectF(cx, cy, circle_size, circle_size))

        # --- рендер SVG в прозрачную картинку ---
        svg_size = self._renderer.defaultSize()
        if not svg_size.isValid():
            svg_size = self.size()

        sw, sh = svg_size.width(), svg_size.height()

        scale = min(circle_size / sw, circle_size / sh) * 0.6 * self._scale  # ИСПРАВЛЕНО
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))

        img = QImage(new_w, new_h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)

        img_painter = QPainter(img)
        img_painter.setRenderHint(QPainter.Antialiasing)
        self._renderer.render(img_painter)
        img_painter.end()

        # --- tint только по альфе ---
        tint = QPainter(img)
        tint.setCompositionMode(QPainter.CompositionMode_SourceIn)
        tint.fillRect(img.rect(), self._main_color)
        tint.end()

        # --- вывод ---
        x = (w - new_w) / 2
        y = (h - new_h) / 2

        painter.drawImage(QPointF(x, y), img)
        painter.end()