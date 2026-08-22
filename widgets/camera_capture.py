from PyQt5 import QtWidgets, QtGui, QtCore
import cv2
from app_settings import open_camera, maybe_mirror


class SettingsPreviewThread(QtCore.QThread):
    """Открывает камеру в фоне и отдаёт кадры для превью настроек."""

    frame_ready = QtCore.pyqtSignal(object)
    status = QtCore.pyqtSignal(str)

    def __init__(self, camera_idx, parent=None):
        super().__init__(parent)
        self.camera_idx = int(camera_idx)
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        cap = open_camera(self.camera_idx)
        if cap is None or not cap.isOpened():
            if self._running:
                self.status.emit("Не удалось открыть камеру")
            return
        while self._running:
            ok, frame = cap.read()
            if not ok:
                self.msleep(20)
                continue
            frame = maybe_mirror(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb.shape
            image = QtGui.QImage(
                rgb.data, width, height, channels * width, QtGui.QImage.Format_RGB888
            ).copy()
            if self._running:
                self.frame_ready.emit(image)
            self.msleep(30)
        cap.release()



class CameraCaptureDialog(QtWidgets.QDialog):
    """Превью веб-камеры и снимок для аватара."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Снимок")
        self.resize(720, 620)
        self.result_pixmap = None
        self._frame = None

        self.preview = QtWidgets.QLabel()
        self.preview.setMinimumSize(640, 480)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setStyleSheet(
            "background: #111; border-radius: 16px; color: white;"
        )
        self.preview.setText("Подключение камеры...")

        self.btn_shot = QtWidgets.QPushButton("Сделать снимок")
        self.btn_shot.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_shot.setMinimumHeight(44)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_cancel.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_cancel.setMinimumHeight(44)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_shot)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(self.preview)
        layout.addLayout(buttons)

        self.btn_shot.setStyleSheet(
            "background: #1dbeb7; color: white; border: none; border-radius: 12px; font-weight: 600;"
        )
        self.btn_cancel.setStyleSheet(
            "background: white; border: 1px solid #D5DEE6; border-radius: 12px;"
        )

        self.btn_shot.clicked.connect(self._capture)
        self.btn_cancel.clicked.connect(self.reject)

        self.cap = open_camera()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        if self.cap is not None and self.cap.isOpened():
            self.timer.start(33)
        else:
            self.preview.setText("Не удалось открыть камеру")
            self.btn_shot.setEnabled(False)

    def _tick(self):
        ok, frame = self.cap.read()
        if not ok:
            return
        frame = maybe_mirror(frame)
        self._frame = frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888).copy()
        pixmap = QtGui.QPixmap.fromImage(image).scaled(
            self.preview.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.preview.setPixmap(pixmap)

    def _capture(self):
        if self._frame is None:
            return
        rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888).copy()
        self.result_pixmap = QtGui.QPixmap.fromImage(image)
        self.accept()

    def closeEvent(self, event):
        self._release()
        super().closeEvent(event)

    def done(self, result):
        self._release()
        super().done(result)

    def _release(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
