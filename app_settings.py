"""Глобальные настройки приложения (QSettings)."""
from __future__ import annotations

import sys
from typing import List, Optional

from PyQt5.QtCore import QSettings

ORG = "RehabTrainer"
APP = "VestibularApp"

KEY_FULLSCREEN = "fullscreen"
KEY_CAMERA = "camera_index"
KEY_MIRROR = "mirror_camera"
KEY_VOLUME = "volume"
KEY_AUDIO_OUTPUT = "audio_output"
KEY_SKELETON = "show_skeleton"
KEY_AUTOPAUSE = "autopause"

DEFAULTS = {
    KEY_FULLSCREEN: True,
    KEY_CAMERA: 0,
    KEY_MIRROR: True,
    KEY_VOLUME: 70,
    KEY_AUDIO_OUTPUT: "",
    KEY_SKELETON: False,
    KEY_AUTOPAUSE: True,
}


def _qs() -> QSettings:
    return QSettings(ORG, APP)


def get_bool(key: str) -> bool:
    value = _qs().value(key, DEFAULTS[key])
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(int(value)) if value is not None else bool(DEFAULTS[key])


def get_int(key: str) -> int:
    return int(_qs().value(key, DEFAULTS[key]))


def get_str(key: str) -> str:
    value = _qs().value(key, DEFAULTS[key])
    if value is None:
        return str(DEFAULTS[key])
    return str(value)


def set_value(key: str, value) -> None:
    _qs().setValue(key, value)


def is_fullscreen() -> bool:
    return get_bool(KEY_FULLSCREEN)


def camera_index() -> int:
    return max(0, get_int(KEY_CAMERA))


def is_mirror() -> bool:
    return get_bool(KEY_MIRROR)


def volume() -> int:
    return max(0, min(100, get_int(KEY_VOLUME)))


def volume_f() -> float:
    return volume() / 100.0


def audio_output() -> str:
    return get_str(KEY_AUDIO_OUTPUT).strip()


def show_skeleton() -> bool:
    return get_bool(KEY_SKELETON)


def autopause_enabled() -> bool:
    return get_bool(KEY_AUTOPAUSE)


def _system_camera_names() -> List[str]:
    try:
        from PyQt5.QtMultimedia import QCameraInfo

        names = []
        seen = set()
        for camera in QCameraInfo.availableCameras():
            if camera.isNull():
                continue
            name = (camera.description() or "").strip() or (camera.deviceName() or "").strip()
            if not name:
                continue
            label = name
            if label in seen:
                label = f"{name} ({len(names)})"
            seen.add(label)
            names.append(label)
        return names
    except Exception:
        return []


def list_cameras(max_index: int = 8) -> List[tuple]:
    """Камеры, которые сейчас есть в системе: (индекс OpenCV, название)."""
    names = _system_camera_names()
    if names:
        return [(index, name) for index, name in enumerate(names)]

    import cv2

    found = []
    misses = 0
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    for index in range(max_index):
        cap = cv2.VideoCapture(index, backend)
        opened = bool(cap.isOpened())
        cap.release()
        if opened:
            found.append((index, f"Камера {index}"))
            misses = 0
        else:
            misses += 1
            if misses >= 2 and (found or index >= 2):
                break
    return found


def open_camera(index: Optional[int] = None):
    import cv2

    cam = camera_index() if index is None else index
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(cam, backend)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam)
    return cap


def maybe_mirror(frame):
    import cv2

    if frame is None:
        return frame
    if is_mirror():
        return cv2.flip(frame, 1)
    return frame


def overlay_pose(frame, pose_landmarks):
    if frame is None or pose_landmarks is None or not show_skeleton():
        return frame
    try:
        import mediapipe as mp

        mp.solutions.drawing_utils.draw_landmarks(
            frame,
            pose_landmarks,
            mp.solutions.pose.POSE_CONNECTIONS,
            mp.solutions.drawing_utils.DrawingSpec(
                color=(29, 190, 183), thickness=2, circle_radius=3
            ),
            mp.solutions.drawing_utils.DrawingSpec(
                color=(44, 62, 80), thickness=2
            ),
        )
    except Exception:
        pass
    return frame


def filter_pause(pause_msg: Optional[str]) -> Optional[str]:
    if not pause_msg:
        return None
    if pause_msg == "Встаньте в кадр" and not autopause_enabled():
        return None
    return pause_msg
