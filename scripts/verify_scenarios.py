from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from analytics.metrics import compute_metrics
from analytics.policy import decide_delta
from analytics.recommend import recommend

BASE = {"n": 10, "tau": 5, "apples_count": 10, "seconds_per_apple": 5}


def make_hist(caught_list, gaps=None):
    hist = []
    dt = datetime(2026, 1, 1)
    day = 0
    for i, c in enumerate(caught_list):
        if gaps:
            day += gaps[i]
        elif i:
            day += 2
        hist.append(
            {
                "apples_count": 10,
                "caught_apples": c,
                "exercise_date": dt + timedelta(days=day),
            }
        )
    return hist


SCENARIOS = {
    "low": ([4, 4, 4, 4, 4, 4], None),
    "high": ([9, 9, 9, 9, 9, 9], None),
    "drop": ([8, 8, 8, 6, 5, 5], None),
    "irreg": ([8, 7, 7, 7, 7, 7], [0, 2, 2, 2, 2, 12]),
    "plateau": ([7, 8, 7, 7, 7, 8], None),
}

for name, (caught, gaps) in SCENARIOS.items():
    h = make_hist(caught, gaps)
    m = compute_metrics(h)
    d = decide_delta(m)
    rec = recommend(1, BASE, h)
    print(
        name,
        caught,
        f"S={m.s_bar:.1f}",
        f"T={m.trend:.1f}",
        f"A={m.regularity}",
        f"drop={int(m.drop)}",
        f"delta={d}",
        f"tau={rec.load['tau']}",
    )
