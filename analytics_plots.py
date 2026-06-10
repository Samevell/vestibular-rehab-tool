"""Графики аналитики (matplotlib + Qt5Agg)."""

import matplotlib

matplotlib.use("Qt5Agg")

from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter

from rehab_config import TARGET_SUCCESS_MAX, TARGET_SUCCESS_MIN


def _format_dates(dates):
    """Приведение exercise_date к списку datetime для оси X."""
    result = []
    for d in dates:
        if d is None:
            continue
        if hasattr(d, "to_pydatetime"):
            result.append(d.to_pydatetime())
        else:
            result.append(d)
    return result


def build_success_figure(sessions):
    """
    График % успешности по датам.

    Args:
        sessions: список dict из metrics.aggregate — keys: record, success, is_valid

    Returns:
        matplotlib.figure.Figure
    """
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)

    if not sessions:
        ax.text(
            0.5,
            0.5,
            "Нет данных о тренировках",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
        )
        ax.set_ylabel("Успешность, %")
        ax.set_xlabel("Дата")
        fig.tight_layout()
        return fig

    dates = _format_dates([s["record"].get("exercise_date") for s in sessions])
    y_pct = [s["success"] * 100.0 for s in sessions]

    valid_x, valid_y = [], []
    invalid_x, invalid_y = [], []

    for i, s in enumerate(sessions):
        if i >= len(dates):
            break
        if s["is_valid"]:
            valid_x.append(dates[i])
            valid_y.append(y_pct[i])
        else:
            invalid_x.append(dates[i])
            invalid_y.append(y_pct[i])

    if valid_x:
        ax.plot(valid_x, valid_y, "o-", color="#0ac5c4", linewidth=2, markersize=7, label="Учтённые")
    if invalid_x:
        ax.scatter(
            invalid_x,
            invalid_y,
            color="#9e9e9e",
            s=70,
            marker="o",
            label="Не учтены",
            zorder=3,
        )

    ax.axhline(TARGET_SUCCESS_MIN * 100, color="#39d192", linestyle="--", linewidth=1.2, label="65%")
    ax.axhline(TARGET_SUCCESS_MAX * 100, color="#fd8c25", linestyle="--", linewidth=1.2, label="85%")
    ax.axhspan(
        TARGET_SUCCESS_MIN * 100,
        TARGET_SUCCESS_MAX * 100,
        alpha=0.08,
        color="#0ac5c4",
    )

    ax.set_ylabel("Успешность, %")
    ax.set_xlabel("Дата")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)

    if dates:
        ax.xaxis.set_major_formatter(DateFormatter("%d.%m.%Y"))
        fig.autofmt_xdate(rotation=25)

    fig.tight_layout()
    return fig
