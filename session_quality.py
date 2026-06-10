"""Классификация качества сессии упражнения 1."""

OUTLIER_MEDIAN_RATIO = 0.5

ZERO_CATCH = "ZERO_CATCH"
TRIVIAL_LOAD = "TRIVIAL_LOAD"
OUTLIER_LOW = "OUTLIER_LOW"

EXCLUDE_REASON_LABELS = {
    ZERO_CATCH: "Нулевая результативность (0 пойманных)",
    TRIVIAL_LOAD: "Тривиальная нагрузка (≤2 яблока)",
    OUTLIER_LOW: "Аномально низкий результат",
}


def session_success(record):
    """Доля пойманных яблок (0..1)."""
    total = record.get("apples_count") or 0
    if total <= 0:
        return 0.0
    caught = record.get("caught_apples") or 0
    return caught / total


def exclude_reason_label(reason_code):
    """Человекочитаемая подпись кода исключения."""
    if reason_code is None:
        return ""
    return EXCLUDE_REASON_LABELS.get(reason_code, str(reason_code))


def classify_session(record, user_median_success=None):
    """
    Валидна ли сессия для рекомендаций и аналитики.

    Returns:
        (is_valid: bool, reason: str | None)  reason — код ZERO_CATCH / TRIVIAL_LOAD / OUTLIER_LOW
    """
    apples = record.get("apples_count") or 0
    caught = record.get("caught_apples") or 0

    if caught == 0:
        return False, ZERO_CATCH

    if apples <= 2:
        return False, TRIVIAL_LOAD

    success = session_success(record)

    if user_median_success is not None and user_median_success > 0:
        if success < user_median_success * OUTLIER_MEDIAN_RATIO:
            return False, OUTLIER_LOW

    return True, None
