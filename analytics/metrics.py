from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class SessionMetrics:
    s_bar: float
    trend: float
    regularity: float
    drop: bool


def _success_rate(session: dict) -> float:
    total = session.get("apples_count") or 0
    caught = session.get("caught_apples") or 0
    if total <= 0:
        return 0.0
    return caught / total * 100.0


def _parse_date(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
    if hasattr(value, "year"):
        return datetime(value.year, value.month, value.day)
    return None


def compute_metrics(sessions: Sequence[dict]) -> Optional[SessionMetrics]:
    """sessions — хронологический порядок (от старых к новым)."""
    if not sessions:
        return None

    rates = [_success_rate(s) for s in sessions]
    s_bar = sum(rates) / len(rates)

    trend = 0.0
    if len(rates) >= 4:
        if len(rates) >= 6:
            recent = sum(rates[-3:]) / 3
            previous = sum(rates[-6:-3]) / 3
        else:
            recent = sum(rates[-2:]) / 2
            previous = sum(rates[-4:-2]) / 2
        trend = recent - previous

    regularity = _regularity(sessions)
    drop = _sharp_drop(rates)

    return SessionMetrics(s_bar=s_bar, trend=trend, regularity=regularity, drop=drop)


def _regularity(sessions: Sequence[dict]) -> float:
    if len(sessions) < 2:
        return 0.0

    last = _parse_date(sessions[-1].get("exercise_date"))
    prev = _parse_date(sessions[-2].get("exercise_date"))
    if not last or not prev:
        return 0.5

    delta_days = abs((last - prev).days)
    if delta_days <= 3:
        return 1.0
    if delta_days <= 7:
        return 0.5
    return 0.0


def _sharp_drop(rates: Sequence[float]) -> bool:
    if len(rates) < 3:
        return False
    third = rates[-3]
    return rates[-1] < third - 15 and rates[-2] < third - 15
