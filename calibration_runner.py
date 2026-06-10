"""Standalone calibration session on label_video (Agent 1)."""
from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import mediapipe as mp
import numpy as np

from calibration import Calibration

mp_pose = mp.solutions.pose


class CalibrationThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    profile_saved = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, user_id, db=None):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.stop_flag = False
        self.calibrated = False
        self.calibration = Calibration()
        self.calibration.calibration_done.connect(self._on_calibration_done)

    def _on_calibration_done(self, data):
        profile = data.get("profile")
        touch_points = data.get("touch_points")
        if profile and self.db and self.user_id:
            self.db.save_user_calibration(self.user_id, profile, touch_points)
            self.profile_saved.emit(profile)
        self.calibrated = True

    def run(self):
        pose = mp_pose.Pose()
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Камера не обнаружена (калибровка).")
            self.finished.emit()
            return

        while cap.isOpened() and not self.calibrated and not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            frame, calibration_completed = self.calibration.run(frame, results)
            self.frame_signal.emit(frame)

            if calibration_completed:
                self.calibrated = True

        cap.release()
        pose.close()
        self.finished.emit()

    def stop(self):
        self.stop_flag = True
