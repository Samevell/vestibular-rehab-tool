"""Generate validation statistics for dissertation section 4."""
from __future__ import annotations

import json
import glob
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics.metrics import compute_metrics
from analytics.policy import decide_delta
from analytics.recommend import recommend

FIG_DIR = ROOT.parent.parent / "trainer_new_int" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_profiles():
    rows = []
    for p in sorted(glob.glob(str(ROOT / "calibration_profiles" / "user_*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        sw = d["shoulder_width"]
        hl = abs(d["head_left_x"] - d["head_neutral_x"])
        hr = abs(d["head_right_x"] - d["head_neutral_x"])
        reach_w = d["right_right"] + d["left_left"]
        reach_h = d["right_up"] + d["right_down"]
        rows.append(
            {
                "user_id": d["user_id"],
                "sw": sw,
                "head_max": max(hl, hr),
                "reach_w": reach_w,
                "reach_h": reach_h,
                "area": reach_w * reach_h,
            }
        )
    return rows


def make_history(rates, day_gap=2, irregular=False):
    hist = []
    dt = datetime(2026, 1, 1)
    for i, r in enumerate(rates):
        n = 10
        c = round(n * r / 100)
        gap = 12 if irregular and i >= 4 else day_gap
        hist.append(
            {
                "apples_count": n,
                "caught_apples": c,
                "exercise_date": dt + timedelta(days=sum([12 if irregular and j >= 4 else day_gap for j in range(i)])),
            }
        )
    return hist


def scenario_table():
    base = {"n": 10, "tau": 5, "apples_count": 10, "seconds_per_apple": 5}
    cases = [
        ("low", [36, 38, 37, 40, 39, 40], False),
        ("high", [88, 90, 85, 92, 87, 91], False),
        ("drop", [82, 80, 78, 55, 50, 48], False),
        ("irreg", [75, 70, 72, 68, 74, 71], True),
        ("plateau", [72, 74, 71, 73, 70, 72], False),
    ]
    print("SCENARIO TABLE")
    for name, rates, irreg in cases:
        h = make_history(rates, irregular=irreg)
        m = compute_metrics(h)
        d = decide_delta(m)
        rec = recommend(1, base, h)
        print(
            name,
            f"S={m.s_bar:.1f}",
            f"T={m.trend:.1f}",
            f"A={m.regularity}",
            f"drop={int(m.drop)}",
            f"delta={d}",
            f"tau={rec.load['tau']}",
        )


def threshold_sensitivity():
    profiles = ["easy", "hard", "mixed", "decline"]
    rate_sets = {
        "easy": [85, 88, 90, 87, 91, 89],
        "hard": [35, 40, 38, 42, 36, 39],
        "mixed": [72, 74, 71, 73, 70, 72],
        "decline": [80, 78, 75, 60, 55, 50],
    }
    hists = [make_history(rate_sets[p]) for p in profiles] * 6

    def decide_custom(m, s_lo=60, s_hi=80, t_lo=-10):
        if m.s_bar < s_lo or m.trend < t_lo or m.drop or m.regularity == 0:
            return -1
        if m.s_bar >= s_hi and m.trend >= 0 and m.regularity >= 0.5:
            return 1
        return 0

    print("THRESHOLD SENSITIVITY")
    for s_lo in [55, 60, 65]:
        ch = sum(
            1
            for h in hists
            if decide_custom(compute_metrics(h), s_lo, 80)
            != decide_delta(compute_metrics(h))
        )
        print(f"S_lo={s_lo} vs 60/80: {ch}/{len(hists)}")
    for s_hi in [75, 80, 85]:
        ch = sum(
            1
            for h in hists
            if decide_custom(compute_metrics(h), 60, s_hi)
            != decide_delta(compute_metrics(h))
        )
        print(f"S_hi={s_hi} vs 60/80: {ch}/{len(hists)}")


def generate_figures():
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np
    except ImportError:
        print("matplotlib not available")
        return

    profiles = load_profiles()
    uids = [p["user_id"] for p in profiles]
    sws = [p["sw"] for p in profiles]
    heads = [p["head_max"] for p in profiles]

    # Profile spread
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].bar([str(u) for u in uids], sws, color="#4C72B0")
    ax[0].set_title("Shoulder width sw (px)")
    ax[0].set_xlabel("User id")
    ax[1].bar([str(u) for u in uids], heads, color="#DD8452")
    ax[1].set_title("Max head offset |delta_x| / sw")
    ax[1].set_xlabel("User id")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calib_profile_spread.png", dpi=150)
    plt.close(fig)

    # Fixed vs personal zone
    fw, fh = 640, 480
    fixed = (0.6 * fw) * (0.6 * fh)
    areas = [p["area"] for p in profiles]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(uids))
    ax.bar(x - 0.2, areas, 0.4, label="Personal reach bbox", color="#55A868")
    ax.bar(x + 0.2, [fixed] * len(uids), 0.4, label="Fixed 20-80% frame", color="#C44E52")
    ax.set_xticks(x)
    ax.set_xticklabels([str(u) for u in uids])
    ax.set_ylabel("Area (px^2)")
    ax.set_title("Reach zone area: calibrated vs fixed")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calib_zone_compare.png", dpi=150)
    plt.close(fig)

    # Threshold sensitivity heatmap
    rate_sets = [
        [85, 88, 90, 87, 91, 89],
        [35, 40, 38, 42, 36, 39],
        [72, 74, 71, 73, 70, 72],
        [80, 78, 75, 60, 55, 50],
        [75, 70, 72, 68, 74, 71],
    ]
    hists = [make_history(r) for r in rate_sets] * 5

    def decide_custom(m, s_lo, s_hi):
        if m.s_bar < s_lo or m.trend < -10 or m.drop or m.regularity == 0:
            return -1
        if m.s_bar >= s_hi and m.trend >= 0 and m.regularity >= 0.5:
            return 1
        return 0

    lo_vals = [50, 55, 60, 65, 70]
    hi_vals = [75, 80, 85, 90]
    mat = np.zeros((len(lo_vals), len(hi_vals)))
    base_dec = [decide_delta(compute_metrics(h)) for h in hists]
    for i, slo in enumerate(lo_vals):
        for j, shi in enumerate(hi_vals):
            if slo >= shi:
                mat[i, j] = np.nan
                continue
            ch = sum(
                1
                for k, h in enumerate(hists)
                if decide_custom(compute_metrics(h), slo, shi) != base_dec[k]
            )
            mat[i, j] = 100 * ch / len(hists)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=40)
    ax.set_xticks(range(len(hi_vals)))
    ax.set_xticklabels(hi_vals)
    ax.set_yticks(range(len(lo_vals)))
    ax.set_yticklabels(lo_vals)
    ax.set_xlabel("Upper threshold S_hi (%)")
    ax.set_ylabel("Lower threshold S_lo (%)")
    ax.set_title("Decision change rate vs base 60/80 (%)")
    for i in range(len(lo_vals)):
        for j in range(len(hi_vals)):
            if not np.isnan(mat[i, j]):
                ax.text(j, i, f"{mat[i,j]:.0f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "threshold_sensitivity.png", dpi=150)
    plt.close(fig)

    # UI mockup
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    panel = mpatches.FancyBboxPatch(
        (0.5, 0.5), 9, 9, boxstyle="round,pad=0.05", fc="#f5f5f5", ec="#333"
    )
    ax.add_patch(panel)
    ax.text(5, 8.7, "Exercise settings (ex. 1)", ha="center", fontsize=14, weight="bold")
    ax.text(1.2, 7.5, "Doctor baseline: n=10, tau=5 s", fontsize=11)
    ax.text(1.2, 6.7, "Recommended: n=10, tau=3 s (delta=+1)", fontsize=11, color="#006600")
    for y, label, color in [
        (5.5, "Apply recommended load", "#4472C4"),
        (4.3, "Restore doctor baseline", "#70AD47"),
        (3.1, "Start training", "#ED7D31"),
    ]:
        btn = mpatches.FancyBboxPatch(
            (2, y - 0.35), 6, 0.9, boxstyle="round,pad=0.02", fc=color, ec="none"
        )
        ax.add_patch(btn)
        ax.text(5, y, label, ha="center", va="center", color="white", fontsize=11)
    ax.text(5, 1.5, "History: last 6 sessions success rates", ha="center", fontsize=10, style="italic")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ui_recommendations.png", dpi=150)
    plt.close(fig)

    # Algorithm flowchart (simple)
    fig, ax = plt.subplots(figsize=(7, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis("off")

    def box(x, y, w, h, text, fc="#E7EFF8"):
        p = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="#333"
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->"))

    box(2.5, 12.5, 5, 1, "History H_e (<=6 sessions)")
    arrow(5, 12.5, 5, 11.8)
    box(2.5, 10.8, 5, 1, "Compute Phi: S_bar, T, A, Drop")
    arrow(5, 10.8, 5, 10.1)
    box(1.5, 8.8, 7, 1.2, "Rule R: delta* in {-1,0,+1}")
    arrow(5, 8.8, 5, 8.1)
    box(2.5, 7.1, 5, 1, "Adj(B_e, delta*, e)")
    arrow(5, 7.1, 5, 6.4)
    box(2.5, 5.4, 5, 1, "Recommended load L_e")
    ax.text(8.2, 9.4, "S<60%\nT<-10\nDrop\nA=0 => -1", fontsize=8)
    ax.text(8.2, 8.5, "S>=80%, T>=0,\nA>=0.5 => +1", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rec_algorithm_flow.png", dpi=150)
    plt.close(fig)

    # Calibration step schematics (for dissertation figures)
    def draw_skeleton(ax, pose="tpose", head_turn=0):
        ax.set_xlim(0, 640)
        ax.set_ylim(480, 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(mpatches.Rectangle((0, 0), 640, 480, fc="#eef2f7", ec="#999"))
        cx, cy = 320, 240
        ax.plot([cx, cx], [cy - 80, cy + 60], color="#333", lw=3)
        if pose == "tpose":
            ax.plot([cx - 120, cx + 120], [cy - 40, cy - 40], color="#333", lw=3)
        else:
            ax.plot([cx, cx + 90], [cy - 40, cy - 20], color="#333", lw=3)
            ax.plot([cx, cx - 60], [cy - 40, cy + 10], color="#333", lw=3)
        hx = cx + head_turn * 40
        ax.add_patch(plt.Circle((hx, cy - 95), 22, fc="#ffe0bd", ec="#333"))
        ax.text(20, 30, "Webcam view", fontsize=10, color="#555")

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    draw_skeleton(ax, "tpose")
    ax.text(320, 420, "Step 1/15: T-pose, distance check", ha="center", fontsize=11, weight="bold")
    ax.plot([220, 420], [300, 300], "g--", lw=1.5)
    ax.text(430, 295, "sw", fontsize=10, color="green")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calib_step_a.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    draw_skeleton(ax, "reach")
    ax.text(320, 420, "Step 4/15: right hand reach left", ha="center", fontsize=11, weight="bold")
    ax.add_patch(plt.Circle((230, 250), 28, fc="#4472C4", ec="white", alpha=0.85))
    ax.add_patch(plt.Circle((210, 245), 28, fc="none", ec="#C44E52", ls="--", lw=2))
    ax.text(250, 280, "adaptive target", fontsize=9, color="#C44E52")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calib_step_b.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    draw_skeleton(ax, "tpose", head_turn=-1)
    ax.text(320, 420, "Step 11/15: head turn left", ha="center", fontsize=11, weight="bold")
    ax.annotate("", xy=(260, 150), xytext=(320, 150), arrowprops=dict(arrowstyle="->", color="#ED7D31"))
    ax.text(250, 130, "delta_x", fontsize=10, color="#ED7D31")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calib_step_c.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    draw_skeleton(ax, "tpose")
    ax.text(320, 420, "Exercise 1: personal spawn zone", ha="center", fontsize=11, weight="bold")
    rect = mpatches.Rectangle((180, 140), 280, 200, fc="#55A868", ec="#2d6a4f", alpha=0.25, lw=2)
    ax.add_patch(rect)
    rect2 = mpatches.Rectangle((128, 96), 384, 288, fc="none", ec="#C44E52", ls="--", lw=2)
    ax.add_patch(rect2)
    ax.text(190, 125, "personal zone", fontsize=9, color="#2d6a4f")
    ax.text(500, 110, "fixed 20-80%", fontsize=9, color="#C44E52")
    ax.add_patch(plt.Circle((350, 220), 28, fc="#4472C4", ec="white"))
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calib_zone.png", dpi=150)
    plt.close(fig)

    print(f"Figures saved to {FIG_DIR}")


if __name__ == "__main__":
    profiles = load_profiles()
    sws = [p["sw"] for p in profiles]
    heads = [p["head_max"] for p in profiles]
    areas = [p["area"] for p in profiles]
    fw, fh = 640, 480
    fixed = (0.6 * fw) * (0.6 * fh)
    print(f"N profiles={len(profiles)}")
    print(f"sw: min={min(sws):.1f} max={max(sws):.1f} mean={sum(sws)/len(sws):.1f} cv={(max(sws)-min(sws))/sum(sws)*len(sws)*100:.1f}%")
    print(f"head max ratio max/min={max(heads)/min(heads):.2f}")
    print(f"personal area mean={sum(areas)/len(areas):.0f} fixed={fixed:.0f} ratio={sum(areas)/len(areas)/fixed:.2f}")
    scenario_table()
    threshold_sensitivity()
    generate_figures()
