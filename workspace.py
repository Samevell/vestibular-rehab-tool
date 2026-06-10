"""Personal reach workspace for exercise 1 (Agent 1)."""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

Point = Tuple[int, int]


@dataclass
class WorkspaceProfile:
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    frame_w: int
    frame_h: int

    @classmethod
    def from_touch_points(
        cls,
        points: Sequence[Point],
        frame_w: int,
        frame_h: int,
        margin_frac: float = 0.05,
    ) -> "WorkspaceProfile":
        """Bounding box from calibration touches with relative padding."""
        if not points:
            return cls(0, frame_w, 0, frame_h, frame_w, frame_h)

        xs = [int(p[0]) for p in points]
        ys = [int(p[1]) for p in points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        span_x = max(x_max - x_min, 1)
        span_y = max(y_max - y_min, 1)
        pad_x = int(span_x * margin_frac)
        pad_y = int(span_y * margin_frac)

        x_min = max(0, x_min - pad_x)
        x_max = min(frame_w, x_max + pad_x)
        y_min = max(0, y_min - pad_y)
        y_max = min(frame_h, y_max + pad_y)

        if x_max <= x_min:
            cx = (x_min + x_max) // 2
            x_min = max(0, cx - 40)
            x_max = min(frame_w, cx + 40)
        if y_max <= y_min:
            cy = (y_min + y_max) // 2
            y_min = max(0, cy - 40)
            y_max = min(frame_h, cy + 40)

        return cls(x_min, x_max, y_min, y_max, frame_w, frame_h)

    def contains(self, x: int, y: int, radius: int = 0) -> bool:
        return (
            self.x_min + radius <= x <= self.x_max - radius
            and self.y_min + radius <= y <= self.y_max - radius
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Optional["WorkspaceProfile"]:
        if not data:
            return None
        try:
            return cls(
                int(data["x_min"]),
                int(data["x_max"]),
                int(data["y_min"]),
                int(data["y_max"]),
                int(data["frame_w"]),
                int(data["frame_h"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def touch_points_to_json(self, points: Sequence[Point]) -> str:
        return json.dumps([[int(x), int(y)] for x, y in points])


def random_point_in_workspace(
    profile: WorkspaceProfile,
    margin: float = 0.1,
    difficulty: float = 1.0,
    target_radius: int = 30,
) -> Point:
    """Random apple position inside the profile, inset by margin and difficulty."""
    span_x = max(profile.x_max - profile.x_min, 1)
    span_y = max(profile.y_max - profile.y_min, 1)
    scale = max(float(difficulty), 0.5)
    inset_x = int(span_x * margin / scale)
    inset_y = int(span_y * margin / scale)

    x_lo = profile.x_min + inset_x + target_radius
    x_hi = profile.x_max - inset_x - target_radius
    y_lo = profile.y_min + inset_y + target_radius
    y_hi = profile.y_max - inset_y - target_radius

    x_lo = max(target_radius, x_lo)
    y_lo = max(target_radius, y_lo)
    x_hi = min(profile.frame_w - target_radius, x_hi)
    y_hi = min(profile.frame_h - target_radius, y_hi)

    if x_lo >= x_hi:
        cx = (profile.x_min + profile.x_max) // 2
        x_lo = max(target_radius, cx - target_radius)
        x_hi = min(profile.frame_w - target_radius, cx + target_radius)
    if y_lo >= y_hi:
        cy = (profile.y_min + profile.y_max) // 2
        y_lo = max(target_radius, cy - target_radius)
        y_hi = min(profile.frame_h - target_radius, cy + target_radius)

    return (random.randint(x_lo, x_hi), random.randint(y_lo, y_hi))


def draw_overlay(frame: np.ndarray, profile: WorkspaceProfile) -> np.ndarray:
    """Draw semi-transparent workspace rectangle on frame."""
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (profile.x_min, profile.y_min),
        (profile.x_max, profile.y_max),
        (105, 212, 20),
        2,
    )
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
    cv2.rectangle(
        frame,
        (profile.x_min, profile.y_min),
        (profile.x_max, profile.y_max),
        (105, 212, 20),
        2,
    )
    return frame
