from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogFormatterMathtext


DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
    / "data"
    / "pso_convergence"
    / "pt2_d01_u100_convergence_runs_with_reference"
    / "curve_relative_final_cost.csv"
)

DEFAULT_OUTPUT_BASENAME = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
    / "pso_relative_final_cost"
)

DEFAULT_RESULTS_DIR = (
    Path(__file__).resolve().parent
    / "results"
    / "pt2_d01_u100_convergence_runs_with_reference"
)

FAMILY_ORDER = ["reference", "pm", "ms", "overshoot", "du_dt"]
FAMILY_LABELS = {
    "reference": "Referenzfall",
    "pm": "PM",
    "ms": r"$M_s$",
    "overshoot": "Überschwingen",
    "du_dt": r"$\mathrm{d}u/\mathrm{d}t$",
}
FAMILY_COLORS = {
    "reference": "#111111",
    "pm": "#1f77b4",
    "ms": "#d62728",
    "overshoot": "#2ca02c",
    "du_dt": "#ff7f0e",
}
HARDNESS_ORDER = ["unconstrained", "easy", "medium", "hard"]
HARDNESS_LABELS = {
    "unconstrained": "ohne Nebenbedingungen",
    "easy": "leicht",
    "medium": "mittel",
    "hard": "hart",
}
HARDNESS_STYLES = {
    "unconstrained": "-",
    "easy": "-",
    "medium": "--",
    "hard": ":",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot relative final-cost curves normalized to the best observed value."
    )
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-basename", type=Path, default=DEFAULT_OUTPUT_BASENAME)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None) -> float:
    if value is None:
        return math.nan
    text = str(value).strip()
    if text == "":
        return math.nan
    return float(text)


def build_rows_from_run_summary(path: Path) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(path):
        grouped[row["config_id"]].append(row)

    out_rows: list[dict[str, str]] = []
    for group_rows in grouped.values():
        feasible_rows = [
            row for row in group_rows if math.isfinite(to_float(row.get("final_best_feasible_cost")))
        ]
        if not feasible_rows:
            continue

        best_observed = min(to_float(row["final_best_feasible_cost"]) for row in feasible_rows)
        ordered_rows = sorted(
            feasible_rows,
            key=lambda row: (
                (to_float(row["final_best_feasible_cost"]) - best_observed) / best_observed
                if best_observed != 0.0
                else math.nan,
                int(float(row["run_id"])),
            ),
        )

        for rank_index, row in enumerate(ordered_rows, start=1):
            cost = to_float(row["final_best_feasible_cost"])
            relative = (cost - best_observed) / best_observed if best_observed != 0.0 else math.nan
            out_rows.append(
                {
                    "family": row["family"],
                    "hardness": row["hardness"],
                    "rank_index": str(rank_index),
                    "relative_deviation_to_best": str(relative),
                }
            )
    return out_rows


def load_plot_rows(data_path: Path) -> list[dict[str, str]]:
    resolved = data_path.resolve()
    if resolved.exists():
        return read_rows(resolved)

    fallback_run_summary = DEFAULT_RESULTS_DIR / "run_summary.csv"
    if fallback_run_summary.exists():
        return build_rows_from_run_summary(fallback_run_summary)

    raise FileNotFoundError(
        f"Neither plot-ready data '{resolved}' nor fallback '{fallback_run_summary}' exist."
    )


def build_series(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[tuple[float, float]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["family"], row["hardness"])].append(row)

    series: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for key, group_rows in grouped.items():
        ordered_rows = sorted(group_rows, key=lambda row: float(row["rank_index"]))
        series[key] = [
            (
                float(row["rank_index"]),
                100.0 * float(row["relative_deviation_to_best"]),
            )
            for row in ordered_rows
        ]
    return series


def main() -> None:
    args = parse_args()
    rows = load_plot_rows(args.data_path)
    series = build_series(rows)

    fig, ax = plt.subplots(figsize=(10.2, 6.0))

    plot_order = [family for family in FAMILY_ORDER if family != "reference"] + ["reference"]

    for family in plot_order:
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
                linewidth=2.0 if family != "reference" else 2.4,
                zorder=3 if family != "reference" else 6,
                label=f"{FAMILY_LABELS[family]} {HARDNESS_LABELS[hardness]}".strip(),
            )

    ax.set_xlim(left=1.0)
    ax.set_ylim(bottom=0.0)
    ax.set_yscale("symlog", linthresh=1e-1)
    ax.set_xlabel("Laufindex nach ansteigendem finalem Bestwert", fontsize=16)
    ax.set_ylabel("Normierte Abweichung zum besten Endwert [%]", fontsize=16)
    y_max = max(
        float(np.max(y))
        for points in series.values()
        for _, y in [([p[0] for p in points], np.array([p[1] for p in points], dtype=float))]
        if len(points) > 0
    )
    yticks = [0.0, 1e-1, 1e0, 1e1, 1e2, 1e3]
    ax.set_yticks([tick for tick in yticks if tick <= y_max * 1.05])
    ax.yaxis.set_major_formatter(LogFormatterMathtext())
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=13)

    output_basename = args.output_basename.resolve()
    fig.tight_layout()
    fig.savefig(output_basename.with_suffix(".pdf"))
    fig.savefig(output_basename.with_suffix(".png"), dpi=180)
    plt.close(fig)

    print(f"Wrote {output_basename.with_suffix('.pdf')}")
    print(f"Wrote {output_basename.with_suffix('.png')}")


if __name__ == "__main__":
    main()
