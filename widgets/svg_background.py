from PyQt5.QtWidgets import QWidget
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QRectF

class SvgBackground(QWidget):
    def __init__(self, svg_path, parent=None, keep_aspect=False):
        super().__init__(parent)

        self.renderer = QSvgRenderer(svg_path)
        self.keep_aspect = keep_aspect

        # всегда не перехватывает клики
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        if not self.renderer.isValid():
            return
            
        painter = None
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            if self.keep_aspect:
                # Исправлено: передаем только painter для keep_aspect
                self.renderer.render(painter)
            else:
                # Исправлено: используем QRectF вместо QRect
                target_rect = QRectF(self.rect())
                self.renderer.render(painter, target_rect)
        except Exception as e:
            print(f"Ошибка отрисовки SVG: {e}")
        finally:
            if painter and painter.isActive():
                painter.end()

class WavesBackground(SvgBackground):
    def __init__(self, parent=None):
        super().__init__("./img/waves.svg", parent, keep_aspect=True)

    def resizeEvent(self, event):
        if self.parent():
            parent_rect = self.parent().rect()

            w = int(parent_rect.width() * 0.6)

            # если сохраняем пропорции — высоту берём из SVG
            svg_size = self.renderer.defaultSize()
            if svg_size.isValid():
                ratio = svg_size.height() / svg_size.width()
                h = int(w * ratio)
            else:
                h = int(parent_rect.height() * 0.6)

            # пример: нижний правый угол
            x = parent_rect.width() - w
            y = parent_rect.height() - h

            self.setGeometry(x, y, w, h)
            self.lower()

        super().resizeEvent(event)

class DotsBackground(SvgBackground):
    def __init__(self, parent=None):
        super().__init__("./img/dots.svg", parent, keep_aspect=True)

    def resizeEvent(self, event):
        if self.parent():
            parent_rect = self.parent().rect()

            w = 300
            h = 200

            x = 0
            y = parent_rect.height() - h

            self.setGeometry(x, y, w, h)
            self.lower()

        super().resizeEvent(event)