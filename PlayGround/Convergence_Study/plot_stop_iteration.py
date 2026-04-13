from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
    / "data"
    / "pso_convergence"
    / "pt2_d01_u100_convergence_runs"
    / "curve_stop_iteration.csv"
)

OUTPUT_BASENAME = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
    / "pso_stop_iteration"
)

FAMILY_ORDER = ["pm", "ms", "overshoot", "du_dt"]
FAMILY_LABELS = {
    "pm": "PM",
    "ms": r"$M_s$",
    "overshoot": "Ueberschwingen",
    "du_dt": r"$\mathrm{d}u/\mathrm{d}t$",
}
FAMILY_COLORS = {
    "pm": "#1f77b4",
    "ms": "#d62728",
    "overshoot": "#2ca02c",
    "du_dt": "#ff7f0e",
}
HARDNESS_ORDER = ["easy", "medium", "hard"]
HARDNESS_LABELS = {
    "easy": "leicht",
    "medium": "mittel",
    "hard": "hart",
}
HARDNESS_STYLES = {
    "easy": "-",
    "medium": "--",
    "hard": ":",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_series(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[tuple[float, float]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["family"], row["hardness"])].append(row)

    series: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for key, group_rows in grouped.items():
        ordered_rows = sorted(group_rows, key=lambda row: float(row["rank_index"]))
        points: list[tuple[float, float]] = []
        for row in ordered_rows:
            run_rank = float(row["rank_index"])
            stop_iteration = float(row["stop_iteration"])
            points.append((run_rank, stop_iteration))
        series[key] = points
    return series


def main() -> None:
    rows = read_rows(DATA_PATH)
    series = build_series(rows)

    fig, ax = plt.subplots(figsize=(10.2, 6.0))

    for family in FAMILY_ORDER:
        for hardness in HARDNESS_ORDER:
            points = series.get((family, hardness))
            if not points:
                continue
            x = np.array([p[0] for p in points], dtype=float)
            y = np.array([p[1] for p in points], dtype=float)
            ax.plot(
                x,
                y,
                color=FAMILY_COLORS[family],
                linestyle=HARDNESS_STYLES[hardness],
                linewidth=2.0,
                label=f"{FAMILY_LABELS[family]} {HARDNESS_LABELS[hardness]}",
            )

    ax.set_xlim(left=1.0)
    ax.set_ylim(bottom=0.0)
    ax.set_xlabel("Laufindex nach ansteigender Anzahl Iterationen bis zum Abbruch")
    ax.set_ylabel("Anzahl Iterationen bis zum Abbruch")
    ax.set_title("Anzahl Iterationen bis zum Abbruch")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", ncol=2, frameon=False)

    fig.tight_layout()
    fig.savefig(OUTPUT_BASENAME.with_suffix(".pdf"))
    fig.savefig(OUTPUT_BASENAME.with_suffix(".png"), dpi=180)
    plt.close(fig)

    print(f"Wrote {OUTPUT_BASENAME.with_suffix('.pdf')}")
    print(f"Wrote {OUTPUT_BASENAME.with_suffix('.png')}")


if __name__ == "__main__":
    main()
