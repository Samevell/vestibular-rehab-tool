from __future__ import annotations

import copy
from typing import Dict, List

from analytics.metrics import SessionMetrics

SPEED_LEVELS: List[str] = ["Медленно", "Средне", "Быстро"]
NECK_LEVELS: List[str] = ["Маленький", "Средний", "Большой"]

N_MIN_EX12 = 1
N_MAX_EX12 = 20
TAU_MIN = 1
TAU_MAX = 30

N_MIN_EX46 = 1
N_MAX_EX46 = 30
TIME_MIN = 10
TIME_MAX = 240

COLOR_MIN = 1
COLOR_MAX = 10


def decide_delta(metrics: SessionMetrics) -> int:
    if (
        metrics.s_bar < 60
        or metrics.trend < -10
        or metrics.drop
        or metrics.regularity == 0
    ):
        return -1
    if metrics.s_bar >= 80 and metrics.trend >= 0 and metrics.regularity >= 0.5:
        return 1
    return 0


def _step_level(levels: List[str], value: str, delta: int) -> str:
    try:
        idx = levels.index(value)
    except ValueError:
        idx = 1 if len(levels) > 1 else 0
    idx = max(0, min(len(levels) - 1, idx + delta))
    return levels[idx]


def adj_load(exercise_id: int, baseline: Dict, delta: int) -> Dict:
    if delta == 0:
        return copy.deepcopy(baseline)

    load = copy.deepcopy(baseline)
    handlers = {
        1: _adj_ex12,
        2: _adj_ex12,
        3: _adj_ex3,
        4: _adj_ex456_speed,
        5: _adj_ex456_speed,
        6: _adj_ex6,
        7: _adj_ex7,
        8: _adj_ex89,
        9: _adj_ex89,
    }
    handler = handlers.get(exercise_id)
    if handler is None:
        return load
    return handler(load, delta)


def _adj_ex12(load: Dict, delta: int) -> Dict:
    n = int(load.get("n", load.get("apples_count", 1)))
    tau = int(load.get("tau", load.get("seconds_per_apple", 5)))

    if delta == -1:
        if tau + 2 <= TAU_MAX:
            load["tau"] = tau + 2
        elif n - 1 >= N_MIN_EX12:
            load["n"] = n - 1
    elif delta == +1:
        if tau - 2 >= TAU_MIN:
            load["tau"] = tau - 2
        elif n + 1 <= N_MAX_EX12:
            load["n"] = n + 1

    load["apples_count"] = load.get("n", n)
    load["seconds_per_apple"] = load.get("tau", tau)
    return _clamp_ex12(load)


def _clamp_ex12(load: Dict) -> Dict:
    load["n"] = max(N_MIN_EX12, min(N_MAX_EX12, int(load.get("n", 1))))
    load["tau"] = max(TAU_MIN, min(TAU_MAX, int(load.get("tau", 5))))
    load["apples_count"] = load["n"]
    load["seconds_per_apple"] = load["tau"]
    return load


def _adj_ex3(load: Dict, delta: int) -> Dict:
    n = int(load.get("n", load.get("apples_count", 1)))
    speed = load.get("speed", "Средне")

    if delta == -1:
        new_speed = _step_level(SPEED_LEVELS, speed, -1)
        if new_speed != speed:
            load["speed"] = new_speed
        elif n - 1 >= N_MIN_EX12:
            load["n"] = n - 1
    elif delta == +1:
        new_speed = _step_level(SPEED_LEVELS, speed, 1)
        if new_speed != speed:
            load["speed"] = new_speed
        elif n + 1 <= N_MAX_EX12:
            load["n"] = n + 1

    load["apples_count"] = load.get("n", n)
    return _clamp_ex12(load)


def _adj_ex456_speed(load: Dict, delta: int) -> Dict:
    n = int(load.get("n", load.get("apples_count", 1)))
    tau = int(load.get("tau", load.get("time_sec", 60)))
    speed = load.get("speed", "Средне")

    if delta == -1:
        new_speed = _step_level(SPEED_LEVELS, speed, -1)
        if new_speed != speed:
            load["speed"] = new_speed
        elif tau + 10 <= TIME_MAX:
            load["tau"] = tau + 10
        elif n - 1 >= N_MIN_EX46:
            load["n"] = n - 1
    elif delta == +1:
        new_speed = _step_level(SPEED_LEVELS, speed, 1)
        if new_speed != speed:
            load["speed"] = new_speed
        elif tau - 10 >= TIME_MIN:
            load["tau"] = tau - 10
        elif n + 1 <= N_MAX_EX46:
            load["n"] = n + 1

    load["apples_count"] = load.get("n", n)
    load["time_sec"] = load.get("tau", tau)
    return _clamp_ex46(load)


def _adj_ex6(load: Dict, delta: int) -> Dict:
    n = int(load.get("n", load.get("apples_count", 1)))
    tau = int(load.get("tau", load.get("time_sec", 60)))

    if delta == -1:
        if tau + 10 <= TIME_MAX:
            load["tau"] = tau + 10
        elif n - 1 >= N_MIN_EX46:
            load["n"] = n - 1
    elif delta == +1:
        if tau - 10 >= TIME_MIN:
            load["tau"] = tau - 10
        elif n + 1 <= N_MAX_EX46:
            load["n"] = n + 1

    load["apples_count"] = load.get("n", n)
    load["time_sec"] = load.get("tau", tau)
    return _clamp_ex46(load)


def _adj_ex7(load: Dict, delta: int) -> Dict:
    n = int(load.get("n", load.get("apples_count", 1)))
    tau = int(load.get("tau", load.get("time_sec", 60)))
    neck = load.get("neck_range", "Средний")

    if delta == -1:
        new_neck = _step_level(NECK_LEVELS, neck, -1)
        if new_neck != neck:
            load["neck_range"] = new_neck
        elif tau + 10 <= TIME_MAX:
            load["tau"] = tau + 10
        elif n - 1 >= N_MIN_EX46:
            load["n"] = n - 1
    elif delta == +1:
        new_neck = _step_level(NECK_LEVELS, neck, 1)
        if new_neck != neck:
            load["neck_range"] = new_neck
        elif tau - 10 >= TIME_MIN:
            load["tau"] = tau - 10
        elif n + 1 <= N_MAX_EX46:
            load["n"] = n + 1

    load["apples_count"] = load.get("n", n)
    load["time_sec"] = load.get("tau", tau)
    if load.get("neck_range") not in NECK_LEVELS:
        load["neck_range"] = "Средний"
    return _clamp_ex46(load)


def _adj_ex89(load: Dict, delta: int) -> Dict:
    n = int(load.get("n", load.get("apples_count", 1)))
    color = int(load.get("color_interval", 2))
    speed = load.get("speed", "Средне")

    if delta == -1:
        new_speed = _step_level(SPEED_LEVELS, speed, -1)
        if new_speed != speed:
            load["speed"] = new_speed
        elif color + 1 <= COLOR_MAX:
            load["color_interval"] = color + 1
        elif n - 1 >= N_MIN_EX46:
            load["n"] = n - 1
    elif delta == +1:
        new_speed = _step_level(SPEED_LEVELS, speed, 1)
        if new_speed != speed:
            load["speed"] = new_speed
        elif color - 1 >= COLOR_MIN:
            load["color_interval"] = color - 1
        elif n + 1 <= N_MAX_EX46:
            load["n"] = n + 1

    load["apples_count"] = load.get("n", n)
    return _clamp_ex89(load)


def _clamp_ex46(load: Dict) -> Dict:
    load["n"] = max(N_MIN_EX46, min(N_MAX_EX46, int(load.get("n", 1))))
    if "tau" in load or "time_sec" in load:
        tau = int(load.get("tau", load.get("time_sec", TIME_MIN)))
        tau = max(TIME_MIN, min(TIME_MAX, tau))
        load["tau"] = tau
        load["time_sec"] = tau
    load["apples_count"] = load["n"]
    return load


def _clamp_ex89(load: Dict) -> Dict:
    load["n"] = max(N_MIN_EX46, min(N_MAX_EX46, int(load.get("n", 1))))
    load["apples_count"] = load["n"]
    if "color_interval" in load:
        load["color_interval"] = max(
            COLOR_MIN, min(COLOR_MAX, int(load["color_interval"]))
        )
    return load


def normalize_baseline_load(exercise_id: int, params: Dict) -> Dict:
    """Приводит сохранённые параметры к единому виду для Adj."""
    load = copy.deepcopy(params)
    if exercise_id in (1, 2):
        load.setdefault("n", load.get("apples_count", 10))
        load.setdefault("tau", load.get("seconds_per_apple", 5))
        return _clamp_ex12(load)
    if exercise_id == 3:
        load.setdefault("n", load.get("apples_count", 5))
        load.setdefault("speed", "Средне")
        return _clamp_ex12(load)
    if exercise_id in (4, 5):
        load.setdefault("n", load.get("apples_count", 8))
        load.setdefault("tau", load.get("time_sec", 60))
        load.setdefault("speed", "Средне")
        return _clamp_ex46(load)
    if exercise_id == 6:
        load.setdefault("n", load.get("apples_count", 10))
        load.setdefault("tau", load.get("time_sec", 90))
        return _clamp_ex46(load)
    if exercise_id == 7:
        load.setdefault("n", load.get("apples_count", 10))
        load.setdefault("tau", load.get("time_sec", 90))
        load.setdefault("neck_range", "Средний")
        return _clamp_ex46(load)
    if exercise_id in (8, 9):
        load.setdefault("n", load.get("apples_count", 10))
        load.setdefault("color_interval", 2)
        load.setdefault("speed", "Средне")
        return _clamp_ex89(load)
    return load
