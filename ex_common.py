"""Общие функции таймера для упражнений 4–7 (как в упражнениях 1–2)."""
import time
import cv2

from cv_text import put_text_ru


def normalize_time_sec(time_sec):
    return float(time_sec)


def apple_is_active(start_time, time_sec):
    if start_time is None:
        return False
    return (time.time() - start_time) < normalize_time_sec(time_sec)


def apple_time_remaining(start_time, time_sec):
    if start_time is None:
        return normalize_time_sec(time_sec)
    return max(0.0, normalize_time_sec(time_sec) - (time.time() - start_time))


def draw_object_timer(frame, start_time, time_sec, y=90):
    if start_time is None:
        return
    remaining = apple_time_remaining(start_time, time_sec)
    put_text_ru(
        frame,
        f"Время: {remaining:.1f} с",
        10,
        y - 26,
        font_size=24,
        color=(0, 0, 255),
    )
