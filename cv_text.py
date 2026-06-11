"""Отрисовка кириллицы на кадрах OpenCV через системный TTF-шрифт."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont

    _PIL_OK = True
except ImportError:
    _PIL_OK = False


def _font_candidates() -> list[Path]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return [
        Path(windir) / "Fonts" / "segoeui.ttf",
        Path(windir) / "Fonts" / "arial.ttf",
        Path(windir) / "Fonts" / "calibri.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]


@lru_cache(maxsize=24)
def _font(size: int):
    if not _PIL_OK:
        return None
    for path in _font_candidates():
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _needs_pil(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def _bgr_rgb(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return int(color[2]), int(color[1]), int(color[0])


def put_text_ru(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    font_size: int = 22,
    color: tuple[int, int, int] = (255, 255, 255),
    stroke: int = 2,
) -> np.ndarray:
    """
    Рисует текст с опорой на верхний левый угол (x, y).
    Для кириллицы использует Pillow + TTF, для латиницы — OpenCV.
    """
    if not text:
        return frame

    if not _PIL_OK or not _needs_pil(text):
        scale = max(0.4, font_size / 32.0)
        cv2.putText(
            frame,
            text,
            (x, y + font_size),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            max(1, stroke),
            cv2.LINE_AA,
        )
        return frame

    font = _font(font_size)
    rgb = _bgr_rgb(color)
    stroke_rgb = (0, 0, 0)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    draw.text(
        (x, y),
        text,
        font=font,
        fill=rgb,
        stroke_width=stroke,
        stroke_fill=stroke_rgb,
    )
    frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
    return frame
