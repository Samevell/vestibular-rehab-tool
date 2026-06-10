"""Рекомендатель параметров упражнения 1 (set-point + EWMA)."""

from rehab_config import (
    APPLE_COUNT_MAX,
    APPLE_COUNT_MIN,
    APPLE_STEP,
    DEFAULT_APPLE_COUNT,
    DEFAULT_SECONDS_PER_APPLE,
    HISTORY_SESSIONS,
    HYSTERESIS_COUNT,
    SECONDS_PER_APPLE_MAX,
    SECONDS_PER_APPLE_MIN,
    SECONDS_STEP,
    TARGET_SUCCESS_MAX,
    TARGET_SUCCESS_MIN,
)
from session_quality import classify_session, session_success
from metrics import compute_ewma_success, median_success


def load_exercise_1_history(db, user_id, limit=HISTORY_SESSIONS):
    """Загрузка и фильтрация валидных сессий упражнения 1."""
    if db is None or user_id is None:
        return []

    raw = db.get_exercise_1_results_raw(user_id, limit=limit * 3)
    if not raw:
        return []

    # от старых к новым
    raw = list(reversed(raw))
    median = median_success(raw)
    valid = []
    for record in raw:
        is_valid, _ = classify_session(record, median)
        if is_valid:
            valid.append(record)
    return valid[-limit:]


def _clamp_apples(value):
    return max(APPLE_COUNT_MIN, min(APPLE_COUNT_MAX, int(value)))


def _clamp_seconds(value):
    return max(SECONDS_PER_APPLE_MIN, min(SECONDS_PER_APPLE_MAX, int(value)))


def compute_load_level(apples_count, seconds_per_apple):
    """Относительный уровень нагрузки."""
    index = apples_count * (10.0 / max(seconds_per_apple, 1))
    if index < 8:
        return "низкая"
    if index < 14:
        return "средняя"
    return "высокая"


def _raw_direction(ewma_success):
    """Направление коррекции: +1 сложнее, -1 легче, 0 без изменений."""
    if ewma_success is None:
        return 0
    if ewma_success > TARGET_SUCCESS_MAX:
        return 1
    if ewma_success < TARGET_SUCCESS_MIN:
        return -1
    return 0


def _session_hysteresis_ok(history, direction):
    """Две последние валидные сессии подтверждают направление коррекции."""
    if len(history) < HYSTERESIS_COUNT:
        return False
    recent = history[-HYSTERESIS_COUNT:]
    if direction > 0:
        return all(session_success(s) > TARGET_SUCCESS_MAX for s in recent)
    if direction < 0:
        return all(session_success(s) < TARGET_SUCCESS_MIN for s in recent)
    return False


def _apply_hysteresis(raw_dir, history):
    """Гистерезис: EWMA вне коридора + 2 сессии подряд с тем же сигналом."""
    if raw_dir == 0:
        return 0
    if _session_hysteresis_ok(history, raw_dir):
        return raw_dir
    return 0


def _adjust_params(apples, seconds, direction):
    """Шаг нагрузки: +1 — усложнить, -1 — упростить."""
    if direction == 0:
        return apples, seconds, []

    reasons = []
    new_apples = apples
    new_seconds = seconds

    if direction > 0:
        if new_seconds > SECONDS_PER_APPLE_MIN:
            new_seconds = _clamp_seconds(new_seconds - SECONDS_STEP)
            reasons.append("Успешность выше целевого коридора — уменьшено время на яблоко")
        elif new_apples < APPLE_COUNT_MAX:
            new_apples = _clamp_apples(new_apples + APPLE_STEP)
            reasons.append("Успешность выше целевого коридора — увеличено количество яблок")
        else:
            reasons.append("Нагрузка уже на максимуме")
    else:
        if new_seconds < SECONDS_PER_APPLE_MAX:
            new_seconds = _clamp_seconds(new_seconds + SECONDS_STEP)
            reasons.append("Успешность ниже целевого коридора — увеличено время на яблоко")
        elif new_apples > APPLE_COUNT_MIN:
            new_apples = _clamp_apples(new_apples - APPLE_STEP)
            reasons.append("Успешность ниже целевого коридора — уменьшено количество яблок")
        else:
            reasons.append("Нагрузка уже на минимуме")

    return new_apples, new_seconds, reasons


def recommend_exercise_1(history, last_params, has_calibration, hysteresis_state=None):
    """
    Рекомендация параметров упражнения 1.

    hysteresis_state — зарезервировано (гистерезис по последним 2 сессиям в history).

    Returns:
        dict: apples_count, seconds_per_apple, reasons, load_level, ewma_success
    """
    reasons = []

    apples = last_params.get("apples_count", DEFAULT_APPLE_COUNT)
    seconds = last_params.get("seconds_per_apple", DEFAULT_SECONDS_PER_APPLE)
    apples = _clamp_apples(apples)
    seconds = _clamp_seconds(seconds)

    if not has_calibration:
        reasons.append("Сначала пройдите калибровку")
        return {
            "apples_count": _clamp_apples(DEFAULT_APPLE_COUNT),
            "seconds_per_apple": _clamp_seconds(DEFAULT_SECONDS_PER_APPLE),
            "reasons": reasons,
            "load_level": compute_load_level(DEFAULT_APPLE_COUNT, DEFAULT_SECONDS_PER_APPLE),
            "ewma_success": None,
        }

    if not history:
        reasons.append("Недостаточно данных — используются параметры по умолчанию")
        return {
            "apples_count": _clamp_apples(DEFAULT_APPLE_COUNT),
            "seconds_per_apple": _clamp_seconds(DEFAULT_SECONDS_PER_APPLE),
            "reasons": reasons,
            "load_level": compute_load_level(DEFAULT_APPLE_COUNT, DEFAULT_SECONDS_PER_APPLE),
            "ewma_success": None,
        }

    ewma_val = compute_ewma_success(history)
    pct = int(round(ewma_val * 100)) if ewma_val is not None else 0
    reasons.append(f"Сглаженная успешность: {pct}% (коридор {int(TARGET_SUCCESS_MIN * 100)}–{int(TARGET_SUCCESS_MAX * 100)}%)")

    raw_dir = _raw_direction(ewma_val)
    apply_dir = _apply_hysteresis(raw_dir, history)

    if raw_dir == 0:
        reasons.append("Успешность в целевом коридоре — параметры без изменений")
    elif apply_dir == 0:
        if len(history) < HYSTERESIS_COUNT:
            reasons.append(
                f"Нужно минимум {HYSTERESIS_COUNT} валидных сессий для изменения нагрузки"
            )
        elif raw_dir > 0:
            reasons.append(
                f"Для повышения нагрузки нужны {HYSTERESIS_COUNT} сессии подряд выше {int(TARGET_SUCCESS_MAX * 100)}%"
            )
        else:
            reasons.append(
                f"Для снижения нагрузки нужны {HYSTERESIS_COUNT} сессии подряд ниже {int(TARGET_SUCCESS_MIN * 100)}%"
            )
    else:
        apples, seconds, adj_reasons = _adjust_params(apples, seconds, apply_dir)
        reasons.extend(adj_reasons)

    if len(history) >= 1:
        last = history[-1]
        reasons.append(
            f"Последняя валидная сессия: {last.get('caught_apples', 0)}/{last.get('apples_count', 0)} "
            f"({int(round(session_success(last) * 100))}%)"
        )

    return {
        "apples_count": apples,
        "seconds_per_apple": seconds,
        "reasons": reasons,
        "load_level": compute_load_level(apples, seconds),
        "ewma_success": ewma_val,
    }
