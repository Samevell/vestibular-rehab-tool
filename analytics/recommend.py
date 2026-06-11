from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from analytics.metrics import SessionMetrics, compute_metrics
from analytics.policy import adj_load, decide_delta, normalize_baseline_load

MIN_SESSIONS = 2
HISTORY_WINDOW = 6


@dataclass
class RecommendResult:
    load: Dict
    delta: int
    sufficient_data: bool
    metrics: Optional[SessionMetrics]
    baseline_used: Dict


def recommend(
    exercise_id: int,
    baseline: Dict,
    history: Sequence[dict],
) -> RecommendResult:
    baseline_load = normalize_baseline_load(exercise_id, baseline)

    sessions = list(history)[-HISTORY_WINDOW:]
    if len(sessions) < MIN_SESSIONS:
        return RecommendResult(
            load=baseline_load,
            delta=0,
            sufficient_data=False,
            metrics=None,
            baseline_used=baseline_load,
        )

    metrics = compute_metrics(sessions)
    if metrics is None:
        return RecommendResult(
            load=baseline_load,
            delta=0,
            sufficient_data=False,
            metrics=None,
            baseline_used=baseline_load,
        )

    delta = decide_delta(metrics)
    recommended = adj_load(exercise_id, baseline_load, delta)

    return RecommendResult(
        load=recommended,
        delta=delta,
        sufficient_data=True,
        metrics=metrics,
        baseline_used=baseline_load,
    )
