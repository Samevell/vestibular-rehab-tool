from PyQt5.QtWidgets import QWidget
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QRectF

from app_paths import resolve_asset

class SvgBackground(QWidget):
    def __init__(self, svg_path, parent=None, keep_aspect=False):
        super().__init__(parent)

        self.renderer = QSvgRenderer(resolve_asset(svg_path))
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
        self.sync_to_parent()
        if event is not None:
            super().resizeEvent(event)

    def sync_to_parent(self):
        if not self.parent():
            return
        parent_rect = self.parent().rect()
        w = int(parent_rect.width() * 0.6)
        svg_size = self.renderer.defaultSize()
        if svg_size.isValid():
            ratio = svg_size.height() / svg_size.width()
            h = int(w * ratio)
        else:
            h = int(parent_rect.height() * 0.6)
        self.setGeometry(parent_rect.width() - w, parent_rect.height() - h, w, h)
        self.lower()


class DotsBackground(SvgBackground):
    def __init__(self, parent=None):
        super().__init__("./img/dots.svg", parent, keep_aspect=True)

    def resizeEvent(self, event):
        self.sync_to_parent()
        if event is not None:
            super().resizeEvent(event)

    def sync_to_parent(self):
        if not self.parent():
            return
        parent_rect = self.parent().rect()
        w = 300
        h = 200
        self.setGeometry(0, parent_rect.height() - h, w, h)
        self.lower()
