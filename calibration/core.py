"""
Калибровка: A — руки в стороны, B — досягаемость каждой руки, C — голова.
После flip: правая рука пользователя = MediaPipe LEFT_*, левая = RIGHT_*.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from cv_text import put_text_ru

mp_pose = mp.solutions.pose

# --- пороги ---
EDGE_MARGIN = 0.08          # доля ширины/высоты — руки не ближе к краю
ARM_LEVEL_TOL = 0.14        # |wrist_y - shoulder_y| норм.
ARMS_DOWN_TOL = 0.18        # запястье ниже плеча → «поднимите руки»
SHOULDER_MIN_PX = 110       # слишком далеко
SHOULDER_MAX_PX = 420       # слишком близко
SPAN_MIN_NORM = 0.22        # руки слишком близко к телу (норм. span)
STAGE_A_HOLD_SEC = 3.0
SKIP_PREV_HOLD_SEC = 3.0
REACH_HOLD_SEC = 0.45
HEAD_NEUTRAL_HOLD_SEC = 2.5
HEAD_POSE_HOLD_SEC = 2.0
HEAD_TURN_MIN = 0.07       # доля ширины плеч — поворот влево/вправо
HEAD_VERT_MIN = 0.055      # доля ширины плеч — наклон вверх/вниз
HEAD_TILT_MIN_DEG = 7.0
TARGET_RADIUS_RATIO = 0.12  # радиус цели от min(w,h)
ADAPT_PULL_RATE = 0.16        # скорость подтягивания круга к кисти
ADAPT_ASSIST_START = 1.0      # сек до начала подстройки
ADAPT_ASSIST_RAMP = 2.5       # сек — полная подстройка к кисти
MIN_AXIS_REACH = 35           # мин. зафиксированный размах (px)
RUNTIME_DIST_PAUSE = 0.40
RUNTIME_PAUSE_SEC = 2.0
SPAWN_MARGIN = 0.12

_PROFILES_DIR = Path(__file__).resolve().parent.parent / "calibration_profiles"


@dataclass
class Profile:
    user_id: int
    frame_w: int
    frame_h: int
    shoulder_width: float
    torso_x: float
    torso_y: float
    arm_span_left: float
    arm_span_right: float
  # правая рука (px от торса)
    right_up: float
    right_down: float
    right_left: float
    right_right: float
  # левая рука
    left_up: float
    left_down: float
    left_left: float
    left_right: float
  # голова (норм. координаты, кроме eye_tilt — градусы)
    head_neutral_x: float
    head_neutral_y: float
    head_neutral_eye_tilt: float
    head_left_x: float
    head_right_x: float
    head_up_y: float
    head_down_y: float
    head_tilt_eye: float
    catch_radius: float

    def reach(self, hand: str) -> dict[str, float]:
        if hand == "left":
            return {
                "up": self.left_up,
                "down": self.left_down,
                "left": self.left_left,
                "right": self.left_right,
            }
        return {
            "up": self.right_up,
            "down": self.right_down,
            "left": self.right_left,
            "right": self.right_right,
        }


@dataclass
class CalibResult:
    frame: np.ndarray
    message: str
    done: bool
    profile: Optional[Profile] = None
    progress: float = 0.0


def _lm(landmarks, idx, w: int, h: int) -> Tuple[float, float, float]:
    p = landmarks.landmark[idx]
    return p.x * w, p.y * h, p.visibility


def user_hand_px(landmarks, w: int, h: int, hand: str = "right") -> Optional[Tuple[int, int]]:
    """Позиция кисти: запястье + указательный палец."""
    if not landmarks:
        return None
    if hand == "right":
        wrist_i, index_i = mp_pose.PoseLandmark.LEFT_WRIST, mp_pose.PoseLandmark.LEFT_INDEX
    else:
        wrist_i, index_i = mp_pose.PoseLandmark.RIGHT_WRIST, mp_pose.PoseLandmark.RIGHT_INDEX
    wx, wy, vw = _lm(landmarks, wrist_i, w, h)
    ix, iy, vi = _lm(landmarks, index_i, w, h)
    if vw < 0.4 and vi < 0.4:
        return None
    return int((wx + ix) / 2), int((wy + iy) / 2)


def _torso(landmarks, w: int, h: int) -> Optional[Tuple[float, float, float]]:
    if not landmarks:
        return None
    lsx, lsy, v1 = _lm(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER, w, h)
    rsx, rsy, v2 = _lm(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER, w, h)
    if v1 < 0.4 or v2 < 0.4:
        return None
    cx, cy = (lsx + rsx) / 2, (lsy + rsy) / 2
    sw = ((rsx - lsx) ** 2 + (rsy - lsy) ** 2) ** 0.5
    return cx, cy, sw


def _head_metrics(landmarks, w: int, h: int) -> Optional[dict[str, float]]:
    """
    Метрики головы, нормированные на ширину плеч — стабильны на любом расстоянии до камеры.
    offset_x/y: смещение носа от центра плеч в долях shoulder_width.
    """
    if not landmarks:
        return None
    nx, ny, vn = _lm(landmarks, mp_pose.PoseLandmark.NOSE, w, h)
    torso = _torso(landmarks, w, h)
    if torso is None or vn < 0.35:
        return None
    tcx, tcy, sw = torso
    sw = max(sw, 60.0)

    le_x, le_y, v1 = _lm(landmarks, mp_pose.PoseLandmark.LEFT_EYE, w, h)
    re_x, re_y, v2 = _lm(landmarks, mp_pose.PoseLandmark.RIGHT_EYE, w, h)

    eye_tilt = 0.0
    if v1 >= 0.2 and v2 >= 0.2:
        eye_tilt = float(np.degrees(np.arctan2(le_y - re_y, le_x - re_x)))

    nose_angle = float(np.degrees(np.arctan2(ny - tcy, nx - tcx)))

    return {
        "offset_x": (nx - tcx) / sw,
        "offset_y": (ny - tcy) / sw,
        "eye_tilt": eye_tilt,
        "nose_angle": nose_angle,
        "shoulder_width": sw,
    }


def profile_path(user_id: int) -> Path:
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return _PROFILES_DIR / f"user_{user_id}.json"


def load_profile(user_id: int) -> Optional[Profile]:
    path = profile_path(user_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Profile(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def save_profile(profile: Profile) -> None:
    path = profile_path(profile.user_id)
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2), encoding="utf-8")


def _draw_hud(frame, title: str, hint: str, progress: float = 0.0) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 72), (40, 40, 40), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    put_text_ru(frame, title, 16, 6, font_size=26, color=(255, 255, 255))
    put_text_ru(frame, hint, 16, 38, font_size=20, color=(200, 230, 255))
    if progress > 0:
        bar_w = int((w - 40) * min(1.0, progress))
        cv2.rectangle(frame, (20, h - 28), (w - 20, h - 12), (60, 60, 60), -1)
        cv2.rectangle(frame, (20, h - 28), (20 + bar_w, h - 12), (0, 200, 120), -1)
    return frame


def _skip_button_rect(w: int, h: int) -> Tuple[int, int, int, int]:
    """Центр нижней части экрана — удобно дотянуться рукой."""
    bw = min(360, max(240, w - 80))
    bh = 54
    x1 = (w - bw) // 2
    y1 = h - 98
    return x1, y1, x1 + bw, y1 + bh


def _point_in_rect(px: int, py: int, rect: Tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = rect
    pad = 10
    return (x1 - pad) <= px <= (x2 + pad) and (y1 - pad) <= py <= (y2 + pad)


def _rounded_rect_filled(
    img: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: Tuple[int, int, int],
    radius: int,
) -> None:
    rw, rh = x2 - x1, y2 - y1
    r = min(radius, rw // 2, rh // 2)
    cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1)
    cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1)
    cv2.circle(img, (x1 + r, y1 + r), r, color, -1)
    cv2.circle(img, (x2 - r, y1 + r), r, color, -1)
    cv2.circle(img, (x1 + r, y2 - r), r, color, -1)
    cv2.circle(img, (x2 - r, y2 - r), r, color, -1)


def _blend_rounded_panel(
    frame: np.ndarray,
    rect: Tuple[int, int, int, int],
    color: Tuple[int, int, int],
    alpha: float,
    radius: int = 16,
) -> None:
    x1, y1, x2, y2 = rect
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(fw, x2), min(fh, y2)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2].copy()
    overlay = np.zeros_like(roi)
    _rounded_rect_filled(overlay, 0, 0, x2 - x1, y2 - y1, color, radius)
    cv2.addWeighted(overlay, alpha, roi, 1.0 - alpha, 0, roi)
    frame[y1:y2, x1:x2] = roi


def _draw_rounded_border(
    frame: np.ndarray,
    rect: Tuple[int, int, int, int],
    color: Tuple[int, int, int],
    thickness: int = 2,
    radius: int = 16,
) -> None:
    x1, y1, x2, y2 = rect
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    cv2.line(frame, (x1 + r, y1), (x2 - r, y1), color, thickness)
    cv2.line(frame, (x1 + r, y2), (x2 - r, y2), color, thickness)
    cv2.line(frame, (x1, y1 + r), (x1, y2 - r), color, thickness)
    cv2.line(frame, (x2, y1 + r), (x2, y2 - r), color, thickness)
    cv2.ellipse(frame, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
    cv2.ellipse(frame, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
    cv2.ellipse(frame, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
    cv2.ellipse(frame, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)


def _draw_skip_previous_button(
    frame: np.ndarray,
    hold_progress: float = 0.0,
    holding: bool = False,
) -> Tuple[int, int, int, int]:
    """Полупрозрачная кнопка «прошлые параметры» по центру внизу."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = _skip_button_rect(w, h)
    radius = 18
    rect = (x1, y1, x2, y2)

    glass_bg = (42, 46, 54) if not holding else (50, 62, 76)
    _blend_rounded_panel(frame, rect, glass_bg, alpha=0.46, radius=radius)

    if hold_progress > 0:
        inner_h = max(4, int((y2 - y1 - 8) * min(1.0, hold_progress)))
        fill_rect = (x1 + 4, y2 - 4 - inner_h, x2 - 4, y2 - 4)
        _blend_rounded_panel(frame, fill_rect, (70, 175, 130), alpha=0.32, radius=radius - 6)

    if holding:
        _blend_rounded_panel(frame, rect, (90, 190, 150), alpha=0.12, radius=radius)

    border_color = (130, 215, 185) if holding else (155, 168, 190)
    _draw_rounded_border(frame, rect, border_color, thickness=1, radius=radius)
    cv2.line(frame, (x1 + radius, y1 + 1), (x2 - radius, y1 + 1), (210, 218, 230), 1)

    bw = x2 - x1
    if holding and hold_progress < 1.0:
        remaining = SKIP_PREV_HOLD_SEC * (1.0 - hold_progress)
        label = f"Удерживайте руку — {remaining:.1f} с"
        put_text_ru(frame, label, x1 + bw // 2 - 130, y1 + 18, font_size=19, color=(248, 252, 255))
    else:
        put_text_ru(frame, "Прошлые параметры", x1 + bw // 2 - 108, y1 + 10, font_size=19, color=(248, 252, 255))
        put_text_ru(
            frame,
            "наведите руку и удержите 3 сек",
            x1 + bw // 2 - 118,
            y1 + 32,
            font_size=14,
            color=(175, 190, 210),
        )
    return x1, y1, x2, y2


def _draw_target(
    frame,
    center: Tuple[int, int],
    radius: int,
    color=(0, 200, 255),
    filled_center: bool = True,
    dashed: bool = False,
):
    if dashed:
        for deg in range(0, 360, 24):
            a1 = math.radians(deg)
            a2 = math.radians(deg + 14)
            x1 = int(center[0] + radius * math.cos(a1))
            y1 = int(center[1] + radius * math.sin(a1))
            x2 = int(center[0] + radius * math.cos(a2))
            y2 = int(center[1] + radius * math.sin(a2))
            cv2.line(frame, (x1, y1), (x2, y2), color, 2)
    else:
        cv2.circle(frame, center, radius, color, 2)
    if filled_center and not dashed:
        cv2.circle(frame, center, max(4, radius // 4), color, -1)


def _axis_reach(tcx: float, tcy: float, hx: float, hy: float, direction: str) -> float:
    """Насколько далеко кисть ушла от торса в заданном направлении (px)."""
    if direction == "right":
        return max(0.0, hx - tcx)
    if direction == "left":
        return max(0.0, tcx - hx)
    if direction == "up":
        return max(0.0, tcy - hy)
    return max(0.0, hy - tcy)


def _point_on_axis(tcx: float, tcy: float, direction: str, dist: float) -> Tuple[int, int]:
    if direction == "right":
        return int(tcx + dist), int(tcy)
    if direction == "left":
        return int(tcx - dist), int(tcy)
    if direction == "up":
        return int(tcx), int(tcy - dist)
    return int(tcx), int(tcy + dist)


def _clamp_target_between_torso_and_ideal(
    tcx: float,
    tcy: float,
    ideal: Tuple[float, float],
    point: Tuple[float, float],
    direction: str,
) -> Tuple[float, float]:
    """Цель не дальше идеала и не ближе торса, чем позволяет направление."""
    ix, iy = ideal
    px, py = point
    ideal_dist = _axis_reach(tcx, tcy, ix, iy, direction)
    point_dist = _axis_reach(tcx, tcy, px, py, direction)
    point_dist = max(MIN_AXIS_REACH * 0.5, min(point_dist, ideal_dist))
    return float(_point_on_axis(tcx, tcy, direction, point_dist)[0]), float(
        _point_on_axis(tcx, tcy, direction, point_dist)[1]
    )

class Calibrator:
    """Стейт-машина: A → B (правая, левая рука) → C (голова)."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.stage = "A"
        self._a_ok_since: Optional[float] = None
        self._hold_since: Optional[float] = None
        self._samples: list = []
        self._previous_profile = load_profile(user_id)
        self._skip_hold_since: Optional[float] = None
        self._skip_hand: Optional[str] = None

        self.frame_w = 640
        self.frame_h = 480
        self.data: dict[str, Any] = {}

        self._hand_steps = [
            ("right", "up", "Правая рука: вверх"),
            ("right", "down", "Правая рука: вниз"),
            ("right", "left", "Правая рука: влево"),
            ("right", "right", "Правая рука: вправо"),
            ("left", "up", "Левая рука: вверх"),
            ("left", "down", "Левая рука: вниз"),
            ("left", "left", "Левая рука: влево"),
            ("left", "right", "Левая рука: вправо"),
        ]
        self._hand_idx = 0

        self._head_steps = [
            ("neutral", "Смотрите прямо в камеру"),
            ("left", "Поверните голову влево"),
            ("right", "Поверните голову вправо"),
            ("up", "Поднимите голову вверх"),
            ("down", "Опустите голову вниз"),
            ("tilt", "Наклоните голову к плечу"),
        ]
        self._head_idx = 0

        self._hand_step_key: Optional[tuple] = None
        self._ideal_target: Optional[Tuple[float, float]] = None
        self._adapt_target: Optional[Tuple[float, float]] = None
        self._step_started: float = 0.0
        self._best_axis: float = 0.0

    def _begin_hand_step(
        self,
        hand: str,
        direction: str,
        tcx: float,
        tcy: float,
        w: int,
        h: int,
    ) -> None:
        key = (hand, direction)
        if self._hand_step_key == key:
            return
        self._hand_step_key = key
        ideal = self._target_for_hand(direction, hand, tcx, tcy, w, h)
        self._ideal_target = (float(ideal[0]), float(ideal[1]))
        self._adapt_target = self._ideal_target
        self._step_started = time.time()
        self._best_axis = 0.0
        self._hold_since = None
        self._samples = []

    def _update_adaptive_target(
        self,
        tcx: float,
        tcy: float,
        hp: Tuple[int, int],
        direction: str,
        ideal: Tuple[float, float],
    ) -> Tuple[float, float]:
        hx, hy = hp
        axis = _axis_reach(tcx, tcy, hx, hy, direction)
        self._best_axis = max(self._best_axis, axis)

        elapsed = time.time() - self._step_started
        time_assist = min(1.0, max(0.0, (elapsed - ADAPT_ASSIST_START) / ADAPT_ASSIST_RAMP))

        ix, iy = ideal
        ideal_dist = max(_axis_reach(tcx, tcy, ix, iy, direction), 1.0)
        reach_ratio = min(1.0, axis / ideal_dist)
        reach_assist = max(0.0, 1.0 - reach_ratio) * 0.85

        blend = max(time_assist, reach_assist)
        goal_x = ix + blend * (hx - ix)
        goal_y = iy + blend * (hy - iy)
        goal_x, goal_y = _clamp_target_between_torso_and_ideal(
            tcx, tcy, ideal, (goal_x, goal_y), direction
        )

        ax, ay = self._adapt_target or ideal
        ax += ADAPT_PULL_RATE * (goal_x - ax)
        ay += ADAPT_PULL_RATE * (goal_y - ay)
        ax, ay = _clamp_target_between_torso_and_ideal(tcx, tcy, ideal, (ax, ay), direction)
        self._adapt_target = (ax, ay)
        return ax, ay

    def _total_steps(self) -> int:
        return 1 + len(self._hand_steps) + len(self._head_steps)

    def _current_step_index(self) -> int:
        if self.stage == "A":
            return 0
        if self.stage == "B":
            return 1 + self._hand_idx
        if self.stage == "C":
            return 1 + len(self._hand_steps) + self._head_idx
        return self._total_steps()

    def tick(self, frame: np.ndarray, landmarks) -> CalibResult:
        h, w = frame.shape[:2]
        self.frame_w, self.frame_h = w, h
        progress = self._current_step_index() / max(1, self._total_steps())
        title = f"Калибровка ({self._current_step_index() + 1}/{self._total_steps()})"

        if landmarks is None:
            out = _draw_hud(frame.copy(), title, "Встаньте в кадр полностью", progress)
            result = CalibResult(out, "Встаньте в кадр полностью", False, progress=progress)
            return self._maybe_skip_with_previous(result, landmarks, w, h)

        if self.stage == "A":
            result = self._stage_a(frame, landmarks, w, h, title, progress)
        elif self.stage == "B":
            result = self._stage_b(frame, landmarks, w, h, title, progress)
        elif self.stage == "C":
            result = self._stage_c(frame, landmarks, w, h, title, progress)
        else:
            result = CalibResult(frame, "Готово", True, self._build_profile(), progress=1.0)

        return self._maybe_skip_with_previous(result, landmarks, w, h)

    def _hand_on_skip_button(
        self, landmarks, w: int, h: int
    ) -> Optional[str]:
        rect = _skip_button_rect(w, h)
        for hand in ("right", "left"):
            hp = user_hand_px(landmarks, w, h, hand)
            if hp and _point_in_rect(hp[0], hp[1], rect):
                return hand
        return None

    def _use_previous_profile(self, w: int, h: int) -> Profile:
        assert self._previous_profile is not None
        prof = Profile(**asdict(self._previous_profile))
        prof.frame_w = w
        prof.frame_h = h
        save_profile(prof)
        return prof

    def _maybe_skip_with_previous(
        self, result: CalibResult, landmarks, w: int, h: int
    ) -> CalibResult:
        if result.done or self._previous_profile is None or self.stage != "A":
            self._skip_hold_since = None
            self._skip_hand = None
            return result

        hold_progress = 0.0
        holding = False
        hand_on_btn: Optional[str] = None

        if landmarks is not None:
            hand_on_btn = self._hand_on_skip_button(landmarks, w, h)
            if hand_on_btn:
                holding = True
                if self._skip_hold_since is None or self._skip_hand != hand_on_btn:
                    self._skip_hold_since = time.time()
                    self._skip_hand = hand_on_btn
                held = time.time() - self._skip_hold_since
                hold_progress = min(1.0, held / SKIP_PREV_HOLD_SEC)
                if held >= SKIP_PREV_HOLD_SEC:
                    prof = self._use_previous_profile(w, h)
                    self.stage = "done"
                    self._skip_hold_since = None
                    self._skip_hand = None
                    out = result.frame.copy()
                    _draw_skip_previous_button(out, 1.0, holding=True)
                    _draw_hud(out, "Калибровка", "Используются прошлые параметры", 1.0)
                    return CalibResult(
                        out,
                        "Используются прошлые параметры",
                        True,
                        prof,
                        progress=1.0,
                    )
            else:
                self._skip_hold_since = None
                self._skip_hand = None

        _draw_skip_previous_button(result.frame, hold_progress, holding)
        return result

    def _stage_a(self, frame, landmarks, w, h, title, progress) -> CalibResult:
        torso = _torso(landmarks, w, h)
        r_hand = user_hand_px(landmarks, w, h, "right")
        l_hand = user_hand_px(landmarks, w, h, "left")

        hint = "Разведите руки в стороны на уровне плеч"
        ok = False

        if torso is None or r_hand is None or l_hand is None:
            hint = "Поднимите и разведите обе руки — должны быть видны в кадре"
        else:
            tcx, tcy, sw = torso
            lsx, lsy, _ = _lm(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER, w, h)
            rsx, rsy, _ = _lm(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER, w, h)
            urx, ury = r_hand  # правая рука пользователя
            ulx, uly = l_hand  # левая рука пользователя

            mx = EDGE_MARGIN * w
            my = EDGE_MARGIN * h

            if urx < mx or urx > w - mx or ulx < mx or ulx > w - mx:
                hint = "Отойдите от экрана — руки не должны выходить за край"
            elif ury < my or ury > h - my or uly < my or uly > h - my:
                hint = "Отойдите — руки обрезаются по вертикали"
            elif sw < SHOULDER_MIN_PX:
                hint = "Подойдите ближе к экрану"
            elif sw > SHOULDER_MAX_PX:
                hint = "Отойдите дальше от экрана"
            elif (ury - lsy) / h > ARMS_DOWN_TOL or (uly - rsy) / h > ARMS_DOWN_TOL:
                hint = "Поднимите руки на уровень плеч"
            elif abs(ury - lsy) / h > ARM_LEVEL_TOL or abs(uly - rsy) / h > ARM_LEVEL_TOL:
                hint = "Держите руки горизонтально на уровне плеч"
            else:
                span = (urx - ulx) / w
                if span < SPAN_MIN_NORM:
                    hint = "Разведите руки шире"
                else:
                    ok = True
                    hint = "Отлично! Не двигайтесь..."

        out = frame.copy()
        if ok:
            if self._a_ok_since is None:
                self._a_ok_since = time.time()
            held = time.time() - self._a_ok_since
            progress_a = min(1.0, held / STAGE_A_HOLD_SEC)
            hint = f"Держите позу... {STAGE_A_HOLD_SEC - held:.1f} с"
            _draw_hud(out, title, hint, progress)
            if held >= STAGE_A_HOLD_SEC:
                tcx, tcy, sw = _torso(landmarks, w, h)
                ur = user_hand_px(landmarks, w, h, "right")
                ul = user_hand_px(landmarks, w, h, "left")
                self.data["torso"] = (tcx, tcy)
                self.data["shoulder_width"] = sw
                self.data["arm_span_left"] = max(20.0, tcx - ul[0])
                self.data["arm_span_right"] = max(20.0, ur[0] - tcx)
                self.stage = "B"
                self._hand_idx = 0
                self._hand_step_key = None
                self._hold_since = None
                self._samples = []
        else:
            self._a_ok_since = None
            _draw_hud(out, title, hint, progress)

        return CalibResult(out, hint, False, progress=progress)

    def _target_for_hand(
        self, direction: str, hand: str, tcx: float, tcy: float, w: int, h: int
    ) -> Tuple[int, int]:
        tcx, tcy = int(tcx), int(tcy)
        reach = 0.38 * min(w, h)
        if hand == "right":
            spans = self.data.get("arm_span_right", reach), self.data.get("arm_span_left", reach)
        else:
            spans = self.data.get("arm_span_left", reach), self.data.get("arm_span_right", reach)

        if direction == "up":
            return tcx, int(max(40, tcy - reach))
        if direction == "down":
            return tcx, int(min(h - 40, tcy + reach))
        if direction == "left":
            return int(max(40, tcx - self.data.get("arm_span_left", reach))), tcy
        return int(min(w - 40, tcx + self.data.get("arm_span_right", reach))), tcy

    def _stage_b(self, frame, landmarks, w, h, title, progress) -> CalibResult:
        if self._hand_idx >= len(self._hand_steps):
            self.stage = "C"
            self._head_idx = 0
            self._hold_since = None
            self._samples = []
            self._hand_step_key = None
            return self.tick(frame, landmarks)

        hand, direction, prompt = self._hand_steps[self._hand_idx]
        tcx, tcy = self.data["torso"]
        self._begin_hand_step(hand, direction, tcx, tcy, w, h)
        ideal = self._ideal_target
        assert ideal is not None

        hp = user_hand_px(landmarks, w, h, hand)
        radius = int(min(w, h) * TARGET_RADIUS_RATIO)

        out = frame.copy()
        _draw_target(out, (int(ideal[0]), int(ideal[1])), radius, color=(90, 90, 90), dashed=True)

        hint = prompt + " — дотянитесь до круга"

        if hp is None:
            _draw_hud(out, title, "Поднимите руку в кадр", progress)
            return CalibResult(out, hint, False, progress=progress)

        ax, ay = self._update_adaptive_target(tcx, tcy, hp, direction, ideal)
        target = (int(ax), int(ay))
        _draw_target(out, target, radius, color=(0, 200, 255))

        if self._best_axis < MIN_AXIS_REACH:
            hint = prompt + " — тяните руку дальше"
        elif (time.time() - self._step_started) > ADAPT_ASSIST_START:
            hint = prompt + " — круг подстраивается под вашу досягаемость"

        dist = ((hp[0] - target[0]) ** 2 + (hp[1] - target[1]) ** 2) ** 0.5
        capture_radius = radius * 1.4

        if dist <= capture_radius and self._best_axis >= MIN_AXIS_REACH * 0.6:
            if self._hold_since is None:
                self._hold_since = time.time()
            self._samples.append((hp[0] - tcx, tcy - hp[1]))
            if time.time() - self._hold_since >= REACH_HOLD_SEC:
                key = f"{hand}_{direction}"
                recorded = max(self._best_axis, MIN_AXIS_REACH * 0.6)
                if self._samples:
                    dxs = [s[0] for s in self._samples]
                    dys = [s[1] for s in self._samples]
                    if direction == "up":
                        recorded = max(recorded, max(dys))
                    elif direction == "down":
                        recorded = max(recorded, max(-d for d in dys))
                    elif direction == "left":
                        recorded = max(recorded, max(-d for d in dxs))
                    else:
                        recorded = max(recorded, max(dxs))
                self.data[key] = max(40.0, recorded)
                self._hand_idx += 1
                self._hand_step_key = None
                self._hold_since = None
                self._samples = []
                hint = "Готово!"
        else:
            self._hold_since = None
            self._samples = []

        _draw_hud(out, title, hint, progress)
        return CalibResult(out, hint, False, progress=progress)

    def _stage_c(self, frame, landmarks, w, h, title, progress) -> CalibResult:
        if self._head_idx >= len(self._head_steps):
            self.stage = "done"
            prof = self._build_profile()
            save_profile(prof)
            out = frame.copy()
            _draw_hud(out, title, "Калибровка завершена!", 1.0)
            return CalibResult(out, "Калибровка завершена", True, prof, progress=1.0)

        step_name, prompt = self._head_steps[self._head_idx]
        metrics = _head_metrics(landmarks, w, h)
        out = frame.copy()
        hold_required = _head_hold_required(step_name)

        if metrics is None:
            self._hold_since = None
            self._samples = []
            _draw_hud(out, title, "Держите голову в кадре", progress)
            return CalibResult(out, prompt, False, progress=progress)

        pose_ok = _head_matches_step(step_name, metrics, self.data)

        if not pose_ok:
            self._hold_since = None
            self._samples = []
            if step_name == "neutral":
                hint = prompt + " — смотрите прямо, не наклоняйте голову"
            elif step_name == "tilt":
                hint = prompt + " — наклоните голову к плечу"
            else:
                hint = prompt + " — выполните движение и удерживайте"
            _draw_hud(out, title, hint, progress)
            return CalibResult(out, hint, False, progress=progress)

        if self._hold_since is None:
            self._hold_since = time.time()
            self._samples = [metrics]
        else:
            self._samples.append(metrics)

        elapsed = time.time() - self._hold_since
        remaining = max(0.0, hold_required - elapsed)
        hint = f"{prompt} — удерживайте {remaining:.1f} с"

        if elapsed >= hold_required:
            self.data[f"head_{step_name}"] = _avg_metrics(self._samples)
            self._head_idx += 1
            self._hold_since = None
            self._samples = []
            hint = "Отлично!"

        _draw_hud(out, title, hint, progress)
        return CalibResult(out, hint, False, progress=progress)

    def _build_profile(self) -> Profile:
        tcx, tcy = self.data["torso"]
        sw = self.data["shoulder_width"]
        return Profile(
            user_id=self.user_id,
            frame_w=self.frame_w,
            frame_h=self.frame_h,
            shoulder_width=sw,
            torso_x=tcx,
            torso_y=tcy,
            arm_span_left=self.data.get("arm_span_left", 80.0),
            arm_span_right=self.data.get("arm_span_right", 80.0),
            right_up=self.data.get("right_up", 120.0),
            right_down=self.data.get("right_down", 120.0),
            right_left=self.data.get("right_left", 80.0),
            right_right=self.data.get("right_right", 80.0),
            left_up=self.data.get("left_up", 120.0),
            left_down=self.data.get("left_down", 120.0),
            left_left=self.data.get("left_left", 80.0),
            left_right=self.data.get("left_right", 80.0),
            head_neutral_x=self.data.get("head_neutral", {}).get("offset_x", 0.0),
            head_neutral_y=self.data.get("head_neutral", {}).get("offset_y", 0.0),
            head_neutral_eye_tilt=self.data.get("head_neutral", {}).get("eye_tilt", 0.0),
            head_left_x=self.data.get("head_left", {}).get("offset_x", -0.08),
            head_right_x=self.data.get("head_right", {}).get("offset_x", 0.08),
            head_up_y=self.data.get("head_up", {}).get("offset_y", -0.08),
            head_down_y=self.data.get("head_down", {}).get("offset_y", 0.08),
            head_tilt_eye=self.data.get("head_tilt", {}).get("eye_tilt", 12.0),
            catch_radius=max(28.0, sw * 0.12),
        )


def _avg_metrics(samples: list) -> dict[str, float]:
    if not samples:
        return {"offset_x": 0.0, "offset_y": 0.0, "eye_tilt": 0.0, "nose_angle": 90.0}
    keys = samples[0].keys()
    return {k: float(np.mean([s[k] for s in samples])) for k in keys}


def _head_matches_step(step_name: str, metrics: dict[str, float], data: dict) -> bool:
    """Проверка, что голова действительно в требуемом положении для текущего шага."""
    if step_name == "neutral":
        return (
            abs(metrics.get("offset_x", 0.0)) < 0.2
            and abs(metrics.get("eye_tilt", 0.0)) < 25.0
        )

    neutral = data.get("head_neutral")
    if not neutral:
        return False

    nx = neutral["offset_x"]
    ny = neutral["offset_y"]
    nt = neutral["eye_tilt"]
    ox = metrics["offset_x"]
    oy = metrics["offset_y"]
    et = metrics["eye_tilt"]

    if step_name == "left":
        return ox < nx - HEAD_TURN_MIN
    if step_name == "right":
        return ox > nx + HEAD_TURN_MIN
    if step_name == "up":
        return oy < ny - HEAD_VERT_MIN
    if step_name == "down":
        return oy > ny + HEAD_VERT_MIN
    if step_name == "tilt":
        if abs(et) < 0.5 and abs(nt) < 0.5:
            return abs(oy - ny) >= HEAD_VERT_MIN * 0.5
        return abs(et - nt) >= HEAD_TILT_MIN_DEG
    return False


def _head_hold_required(step_name: str) -> float:
    return HEAD_NEUTRAL_HOLD_SEC if step_name == "neutral" else HEAD_POSE_HOLD_SEC

# --- использование в упражнении ---

_runtime_bad_since: Optional[float] = None


def reset_runtime_guard() -> None:
    global _runtime_bad_since
    _runtime_bad_since = None


def check_runtime(profile: Profile, landmarks, w: int, h: int) -> Optional[str]:
    """None если можно играть, иначе текст паузы."""
    global _runtime_bad_since
    torso = _torso(landmarks, w, h)
    if torso is None:
        msg = "Встаньте в кадр"
        return _pause_hold(msg)

    _, _, sw = torso
    ratio = abs(sw - profile.shoulder_width) / max(profile.shoulder_width, 1.0)
    if ratio > RUNTIME_DIST_PAUSE:
        if sw < profile.shoulder_width * (1 - RUNTIME_DIST_PAUSE):
            msg = "Подойдите ближе к экрану"
        else:
            msg = "Отойдите от экрана"
        return _pause_hold(msg)

    _runtime_bad_since = None
    return None


def _pause_hold(msg: str) -> Optional[str]:
    global _runtime_bad_since
    now = time.time()
    if _runtime_bad_since is None:
        _runtime_bad_since = now
        return None
    if now - _runtime_bad_since >= RUNTIME_PAUSE_SEC:
        return msg
    return None


def torso_shift(profile: Profile, landmarks, w: int, h: int) -> Tuple[float, float]:
    torso = _torso(landmarks, w, h)
    if torso is None:
        return 0.0, 0.0
    tcx, tcy, _ = torso
    return tcx - profile.torso_x, tcy - profile.torso_y


def spawn_object(
    profile: Profile,
    shift: Tuple[float, float],
    hand: str = "right",
    margin: float = SPAWN_MARGIN,
) -> Tuple[int, int]:
    """Случайная точка в персональной зоне руки."""
    reach = profile.reach(hand)
    tcx = profile.torso_x + shift[0]
    tcy = profile.torso_y + shift[1]
    m = margin
    x = tcx + random.uniform(-reach["left"] * (1 - m), reach["right"] * (1 - m))
    y = tcy + random.uniform(-reach["down"] * (1 - m), reach["up"] * (1 - m))
    pad = int(profile.catch_radius) + 10
    x = int(max(pad, min(profile.frame_w - pad, x)))
    y = int(max(pad, min(profile.frame_h - pad, y)))
    return x, y


def spawn_zone_bounds(
    profile: Profile,
    shift: Tuple[float, float],
    hand: str = "right",
    margin: float = SPAWN_MARGIN,
) -> Tuple[int, int, int, int]:
    """Прямоугольник зоны появления яблок (как в spawn_object)."""
    reach = profile.reach(hand)
    tcx = profile.torso_x + shift[0]
    tcy = profile.torso_y + shift[1]
    m = margin
    x1 = int(tcx - reach["left"] * (1 - m))
    x2 = int(tcx + reach["right"] * (1 - m))
    y1 = int(tcy - reach["up"] * (1 - m))
    y2 = int(tcy + reach["down"] * (1 - m))
    pad = int(profile.catch_radius) + 10
    x1 = max(pad, x1)
    y1 = max(pad, y1)
    x2 = min(profile.frame_w - pad, x2)
    y2 = min(profile.frame_h - pad, y2)
    return x1, y1, x2, y2


def draw_spawn_zone(
    frame: np.ndarray,
    profile: Profile,
    shift: Tuple[float, float],
    hand: str = "right",
) -> np.ndarray:
    """Рисует на кадре зону, где может появиться яблоко."""
    x1, y1, x2, y2 = spawn_zone_bounds(profile, shift, hand)
    if x2 <= x1 or y2 <= y1:
        return frame

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 180, 70), -1)
    cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 100), 2)

    tcx = int(profile.torso_x + shift[0])
    tcy = int(profile.torso_y + shift[1])
    cv2.drawMarker(frame, (tcx, tcy), (0, 220, 100), cv2.MARKER_CROSS, 14, 2)
    put_text_ru(frame, "Зона появления цели", x1 + 4, max(20, y1 - 6), font_size=18, color=(0, 230, 110))
    return frame


def print_profile_summary(profile: Profile) -> None:
    """Вывод в консоль параметров профиля для упражнения."""
    path = profile_path(profile.user_id)
    sep = "=" * 58
    print(f"\n{sep}")
    print("  РЕЗУЛЬТАТЫ КАЛИБРОВКИ — параметры упражнения")
    print(sep)
    print(f"  Пациент: №{profile.user_id}")
    print(f"  Файл профиля: {path}")
    print()
    print("  --- Дистанция и положение ---")
    print(f"  Ширина плеч (эталон):     {profile.shoulder_width:.0f} px")
    print(f"  Центр торса:              ({profile.torso_x:.0f}, {profile.torso_y:.0f})")
    print(f"  Допуск смены дистанции:   ±{RUNTIME_DIST_PAUSE * 100:.0f}%")
    print()
    print("  --- Досягаемость правой руки (px от торса) ---")
    print(
        f"  вверх {profile.right_up:.0f}  |  вниз {profile.right_down:.0f}  |  "
        f"влево {profile.right_left:.0f}  |  вправо {profile.right_right:.0f}"
    )
    print("  --- Досягаемость левой руки (px от торса) ---")
    print(
        f"  вверх {profile.left_up:.0f}  |  вниз {profile.left_down:.0f}  |  "
        f"влево {profile.left_left:.0f}  |  вправо {profile.left_right:.0f}"
    )
    print()
    print("  --- Голова (норм. смещение, доли ширины плеч) ---")
    print(
        f"  нейтраль:  x {profile.head_neutral_x:+.3f}  y {profile.head_neutral_y:+.3f}  "
        f"наклон {profile.head_neutral_eye_tilt:+.1f}°"
    )
    print(
        f"  влево x {profile.head_left_x:+.3f}  |  вправо x {profile.head_right_x:+.3f}  |  "
        f"вверх y {profile.head_up_y:+.3f}  |  вниз y {profile.head_down_y:+.3f}"
    )
    print(f"  наклон (tilt): {profile.head_tilt_eye:+.1f}°")
    print()
    print("  --- Упражнение 1 (яблоко) ---")
    print(f"  Радиус захвата цели:      {profile.catch_radius:.0f} px")
    print(f"  Зона спавна (отступ):     {SPAWN_MARGIN * 100:.0f}% от досягаемости")
    r = profile.reach("right")
    eff = {k: r[k] * (1 - SPAWN_MARGIN) for k in r}
    print(
        f"  Зона правой руки:  ←{eff['left']:.0f}  →{eff['right']:.0f}  "
        f"↑{eff['up']:.0f}  ↓{eff['down']:.0f} px"
    )
    print(sep + "\n")


def head_ok(profile: Profile, landmarks, w: int, h: int, mode: str = "neutral") -> bool:
    m = _head_metrics(landmarks, w, h)
    if m is None:
        return False

    if mode == "neutral":
        return (
            abs(m["offset_x"] - profile.head_neutral_x) < 0.14
            and abs(m["offset_y"] - profile.head_neutral_y) < 0.12
            and abs(m["eye_tilt"] - profile.head_neutral_eye_tilt) < 16.0
        )

    def _between(val, a, b, frac=0.35):
        lo, hi = min(a, b), max(a, b)
        span = hi - lo
        if span < 1e-5:
            return abs(val - lo) < 0.04
        return val <= lo + span * (0.5 + frac) and val >= lo + span * (0.5 - frac)

    if mode == "left":
        return m["offset_x"] <= profile.head_neutral_x + (
            profile.head_left_x - profile.head_neutral_x
        ) * 0.55
    if mode == "right":
        return m["offset_x"] >= profile.head_neutral_x + (
            profile.head_right_x - profile.head_neutral_x
        ) * 0.55
    if mode == "up":
        return m["offset_y"] <= profile.head_neutral_y + (
            profile.head_up_y - profile.head_neutral_y
        ) * 0.55
    if mode == "down":
        return m["offset_y"] >= profile.head_neutral_y + (
            profile.head_down_y - profile.head_neutral_y
        ) * 0.55
    if mode == "tilt":
        return abs(m["eye_tilt"] - profile.head_neutral_eye_tilt) >= abs(
            profile.head_tilt_eye - profile.head_neutral_eye_tilt
        ) * 0.45
    return False


def catch_ok(
    profile: Profile,
    hand_xy: Optional[Tuple[int, int]],
    apple_xy: Tuple[int, int],
) -> bool:
    if hand_xy is None:
        return False
    d = np.linalg.norm(np.array(hand_xy) - np.array(apple_xy))
    return d < profile.catch_radius
