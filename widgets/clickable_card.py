from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QRectF, pyqtProperty
from PyQt5.QtGui import QColor, QPainter, QBrush, QPainterPath, QPen


class Ripple:
    def __init__(self, pos):
        self.pos = pos
        self.radius = 0
        self.opacity = 0.25


class ClickableCard(QFrame):
    clicked = pyqtSignal()

    _groups = {}

    def __init__(
        self,
        parent=None,
        radius=16,

        # базовые цвета
        bg_color="#ffffff",
        hover_color="#f9fffe",
        pressed_color="#eaeaea",

        # selected цвета
        selected_bg="#f0f9f9",
        selected_border="#69d5d7",
        selected_overlay_alpha=40
    ):
        super().__init__(parent)

        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._radius = radius

        # --- базовые цвета ---
        self._bg_color = QColor(bg_color)
        self._hover_color = QColor(hover_color)
        self._pressed_color = QColor(pressed_color)

        # --- selected ---
        self._selected_bg = QColor(selected_bg)
        self._selected_border = QColor(selected_border)
        self._selected_overlay_alpha = selected_overlay_alpha

        self._current_color = QColor(bg_color)

        self._enabled = True

        # --- selectable ---
        self._choosable = False
        self._selected = False
        self._group = None

        # --- тень ---
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        # --- ripple ---
        self.ripples = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ripples)
        self.timer.start(16)

    # ---------------- PROPERTIES ----------------
    def getChoosable(self):
        return self._choosable

    def setChoosable(self, value):
        self._choosable = value

    choosable = pyqtProperty(bool, fget=getChoosable, fset=setChoosable)

    # ---------------- GROUP ----------------
    def setGroup(self, name):
        self._group = name
        if name not in ClickableCard._groups:
            ClickableCard._groups[name] = []
        if self not in ClickableCard._groups[name]:
            ClickableCard._groups[name].append(self)

    def select(self):
        if not self._choosable:
            return

        # сбрасываем ВСЕ карточки группы
        if self._group:
            for card in ClickableCard._groups.get(self._group, []):
                card._selected = False
                card._current_color = card._bg_color
                card.update()

        # выбираем текущую
        self._selected = True
        self._current_color = self._selected_bg
        self.update()

    def resetSelection(self):
        self._selected = False
        self._current_color = self._bg_color
        self.update()

    @staticmethod
    def resetGroup(name):
        for card in ClickableCard._groups.get(name, []):
            card._selected = False
            card._current_color = card._bg_color
            card.update()

    @staticmethod
    def resetAll():
        for group in ClickableCard._groups.values():
            for card in group:
                card._selected = False
                card._current_color = card._bg_color
                card.update()

    # ---------------- EVENTS ----------------
    def enterEvent(self, event):
        if not self._enabled:
            return

        if not self._selected:
            self._current_color = self._hover_color

        self.update()

    def leaveEvent(self, event):
        if not self._enabled:
            return

        if not self._selected:
            self._current_color = self._bg_color

        self.update()

    def mousePressEvent(self, event):
        if not self._enabled:
            return

        if not self._selected:
            self._current_color = self._pressed_color

        self.ripples.append(Ripple(event.pos()))
        self.update()

    def mouseReleaseEvent(self, event):
        if not self._enabled:
            return

        if self.rect().contains(event.pos()):
            if self._choosable:
                if not self._selected:
                    self.select()
            else:
                # обычное поведение кнопки
                self._current_color = self._hover_color

            self.clicked.emit()

        else:
            # если отпустили вне — вернуть базовый цвет
            if not self._choosable or not self._selected:
                self._current_color = self._bg_color

        self.update()

    # ---------------- RIPPLE ----------------
    def update_ripples(self):
        if not self.ripples:
            return

        updated = []
        for r in self.ripples:
            r.radius += 4
            r.opacity -= 0.03
            if r.opacity > 0:
                updated.append(r)

        self.ripples = updated
        self.update()

    # ---------------- PAINT ----------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())

        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        painter.setClipPath(path)

        # --- фон ---
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._current_color))
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # --- selected ---
        if self._selected:
            # overlay (мягкий tint)
            overlay = QColor(self._selected_border)
            overlay.setAlpha(self._selected_overlay_alpha)
            painter.setBrush(overlay)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, self._radius, self._radius)

            # border
            pen = QPen(self._selected_border)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), self._radius, self._radius)

        # --- ripple ---
        for r in self.ripples:
            alpha = int(max(0, min(255, r.opacity * 255)))
            color = QColor(0, 0, 0, alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(r.pos, r.radius, r.radius)