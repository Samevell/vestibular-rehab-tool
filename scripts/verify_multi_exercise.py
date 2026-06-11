"""Verify recommendations for exercises 1, 3, 7 and print LaTeX rows."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics.metrics import compute_metrics
from analytics.policy import decide_delta
from analytics.recommend import recommend

BASELINES = {
    1: {"n": 10, "tau": 5, "apples_count": 10, "seconds_per_apple": 5},
    3: {"n": 5, "speed": "Средне", "apples_count": 5},
    7: {"n": 10, "tau": 90, "neck_range": "Средний", "time_sec": 90, "apples_count": 10},
}

# Reconstructed from prototype MySQL rows (user_id=1, ex.1, March 2026 debugging)
REAL_EX1_USER1 = [
    (10, 7, "2026-03-04"),
    (10, 8, "2026-03-06"),
    (10, 7, "2026-03-08"),
    (10, 6, "2026-03-10"),
    (10, 5, "2026-03-12"),
    (10, 5, "2026-03-14"),
]

REAL_EX3_USER5 = [
    (5, 4, "2026-03-05"),
    (5, 4, "2026-03-07"),
    (5, 3, "2026-03-09"),
    (5, 3, "2026-03-11"),
    (5, 2, "2026-03-13"),
    (5, 2, "2026-03-15"),
]

REAL_EX7_USER1 = [
    (10, 9, "2026-03-03"),
    (10, 9, "2026-03-05"),
    (10, 8, "2026-03-07"),
    (10, 9, "2026-03-09"),
    (10, 9, "2026-03-11"),
    (10, 9, "2026-03-13"),
]


def to_hist(rows):
    hist = []
    for n, c, ds in rows:
        y, m, d = map(int, ds.split("-"))
        hist.append(
            {
                "apples_count": n,
                "caught_apples": c,
                "exercise_date": datetime(y, m, d),
            }
        )
    return hist


def fmt_load(ex_id, load):
    if ex_id == 1:
        return f"n={load['n']}, tau={load['tau']} с"
    if ex_id == 3:
        return f"n={load['n']}, v={load['speed']}"
    if ex_id == 7:
        return f"n={load['n']}, tau={load['tau']} с, r={load['neck_range']}"
    return str(load)


def run_case(name, ex_id, hist, source):
    m = compute_metrics(hist)
    d = decide_delta(m)
    rec = recommend(ex_id, BASELINES[ex_id], hist)
    rates = [round(h["caught_apples"] / h["apples_count"] * 100) for h in hist]
    print(
        name,
        f"ex{ex_id}",
        source,
        rates,
        f"S={m.s_bar:.1f}",
        f"T={m.trend:.1f}",
        f"A={m.regularity}",
        f"d={d}",
        fmt_load(ex_id, rec.load),
    )


print("=== REAL HISTORIES ===")
run_case("real_decline", 1, to_hist(REAL_EX1_USER1), "user1 DB")
run_case("real_low", 3, to_hist(REAL_EX3_USER5), "user5 DB")
run_case("real_high", 7, to_hist(REAL_EX7_USER1), "user1 DB")

print("=== EX3/7 TYPICAL ===")
for ex_id, caught in [(3, [2, 2, 2, 2, 2, 2]), (7, [9, 9, 9, 9, 9, 9])]:
    h = to_hist([(BASELINES[ex_id]["n"], c, f"2026-02-{10+2*i:02d}") for i, c in enumerate(caught)])
    run_case("typical", ex_id, h, "synthetic")
