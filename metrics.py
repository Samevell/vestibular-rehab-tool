"""Метрики для аналитики и рекомендаций."""

from rehab_config import EWMA_ALPHA, TARGET_SUCCESS_MAX, TARGET_SUCCESS_MIN
from session_quality import classify_session, session_success


def ewma(values, alpha=EWMA_ALPHA):
    """Экспоненциально взвешенное среднее (от старых к новым)."""
    if not values:
        return None
    result = float(values[0])
    for v in values[1:]:
        result = alpha * float(v) + (1.0 - alpha) * result
    return result


def compute_ewma_success(records, alpha=EWMA_ALPHA):
    """EWMA успешности по списку записей (хронологически от старых к новым)."""
    rates = [session_success(r) for r in records]
    return ewma(rates, alpha)


def median_success(records):
    """Медиана успешности по записям."""
    rates = sorted(session_success(r) for r in records)
    if not rates:
        return None
    mid = len(rates) // 2
    if len(rates) % 2:
        return rates[mid]
    return (rates[mid - 1] + rates[mid]) / 2.0


def in_target_band(success_rate):
    """Успешность в целевом коридоре 65–85%."""
    return TARGET_SUCCESS_MIN <= success_rate <= TARGET_SUCCESS_MAX


def in_target_band_stats(records):
    """Доля валидных сессий в коридоре 65–85%."""
    if not records:
        return {"count": 0, "total": 0, "pct": 0.0}
    total = len(records)
    count = sum(1 for r in records if in_target_band(session_success(r)))
    return {"count": count, "total": total, "pct": count / total}


def trend(success_rates, window=3, threshold=0.05):
    """
    Тренд успешности: сравнение последних window сессий с предыдущими window.

    Returns:
        'рост' | 'снижение' | 'стабильно' | 'недостаточно данных'
    """
    if len(success_rates) < 2:
        return "недостаточно данных"
    recent = success_rates[-window:]
    older = success_rates[-2 * window : -window]
    if not older:
        return "недостаточно данных"
    recent_avg = sum(recent) / len(recent)
    older_avg = sum(older) / len(older)
    delta = recent_avg - older_avg
    if delta > threshold:
        return "рост"
    if delta < -threshold:
        return "снижение"
    return "стабильно"


def aggregate(db, user_id, exercise=1, limit=50):
    """
    Сводка аналитики для пользователя (упражнение 1).

    Returns:
        dict: sessions, ewma, trend, in_target_band, median_success, valid_count
    """
    if exercise != 1 or db is None or user_id is None:
        return {
            "sessions": [],
            "ewma": None,
            "trend": "недостаточно данных",
            "in_target_band": {"count": 0, "total": 0, "pct": 0.0},
            "median_success": None,
            "valid_count": 0,
        }

    raw = db.get_exercise_1_results_raw(user_id, limit=limit)
    chronological = list(reversed(raw))
    median = median_success(chronological)

    sessions = []
    for record in chronological:
        is_valid, reason = classify_session(record, median)
        sessions.append(
            {
                "record": record,
                "success": session_success(record),
                "is_valid": is_valid,
                "exclude_reason": reason,
            }
        )

    valid_records = [s["record"] for s in sessions if s["is_valid"]]
    valid_rates = [s["success"] for s in sessions if s["is_valid"]]

    return {
        "sessions": sessions,
        "ewma": compute_ewma_success(valid_records),
        "trend": trend(valid_rates),
        "in_target_band": in_target_band_stats(valid_records),
        "median_success": median,
        "valid_count": len(valid_records),
    }
