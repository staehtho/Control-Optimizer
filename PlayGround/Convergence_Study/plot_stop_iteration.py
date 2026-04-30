from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_RESULTS_DIR = (
    Path(__file__).resolve().parent
    / "results"
    / "pt2_d01_u200_convergence_runs_with_reference"
)

DEFAULT_DATA_PATH = DEFAULT_RESULTS_DIR / "run_summary.csv"

DEFAULT_OUTPUT_BASENAME = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
    / "pso_stop_iteration"
)

FAMILY_ORDER = ["reference", "pm", "ms", "overshoot", "du_dt"]
FAMILY_LABELS = {
    "reference": "Referenzfall",
    "pm": r"$\varphi_m$",
    "ms": r"$S_{max}$",
    "overshoot": r"$os$",
    "du_dt": r"$du/dt$",
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
    parser = argparse.ArgumentParser(description="Plot stop-iteration curves.")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-basename", type=Path, default=DEFAULT_OUTPUT_BASENAME)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_rows_from_run_summary(path: Path) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(path):
        grouped[row["config_id"]].append(row)

    out_rows: list[dict[str, str]] = []
    family_hardness_to_config: dict[tuple[str, str], str] = {}
    for group_rows in grouped.values():
        exemplar = group_rows[0]
        key = (exemplar["family"], exemplar["hardness"])
        previous = family_hardness_to_config.get(key)
        if previous is not None and previous != exemplar["config_id"]:
            raise ValueError(
                "Ambiguous plot grouping detected: "
                f"{key!r} is used by both '{previous}' and '{exemplar['config_id']}'."
            )
        family_hardness_to_config[key] = exemplar["config_id"]

        ordered_rows = sorted(
            (row for row in group_rows if row.get("stop_iteration", "").strip() != ""),
            key=lambda row: (float(row["stop_iteration"]), int(float(row["run_id"]))),
        )

        for rank_index, row in enumerate(ordered_rows, start=1):
            out_rows.append(
                {
                    "config_id": row["config_id"],
                    "family": row["family"],
                    "hardness": row["hardness"],
                    "rank_index": str(rank_index),
                    "stop_iteration": row["stop_iteration"],
                }
            )
    return out_rows


def load_plot_rows(data_path: Path) -> list[dict[str, str]]:
    resolved = data_path.resolve()
    if resolved.exists():
        rows = read_rows(resolved)
        if rows and "stop_iteration" in rows[0] and "rank_index" in rows[0]:
            return rows
        if rows and "stop_iteration" in rows[0] and "config_id" in rows[0]:
            return build_rows_from_run_summary(resolved)
        raise ValueError(f"Unsupported input format for stop-iteration plot: '{resolved}'")

    fallback_run_summary = DEFAULT_RESULTS_DIR / "run_summary.csv"
    if fallback_run_summary.exists():
        return build_rows_from_run_summary(fallback_run_summary)

    raise FileNotFoundError(
        f"Neither plot-ready data '{resolved}' nor fallback '{fallback_run_summary}' exist."
    )


def build_series(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[tuple[float, float]]]:
    family_hardness_to_config: dict[tuple[str, str], str] = {}
    for row in rows:
        config_id = str(row.get("config_id", ""))
        key = (row["family"], row["hardness"])
        previous = family_hardness_to_config.get(key)
        if config_id and previous is not None and previous != config_id:
            raise ValueError(
                "Ambiguous plot grouping detected: "
                f"{key!r} is used by both '{previous}' and '{config_id}'."
            )
        if config_id:
            family_hardness_to_config[key] = config_id

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["family"], row["hardness"])].append(row)

    series: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for key, group_rows in grouped.items():
        ordered_rows = sorted(group_rows, key=lambda row: float(row["rank_index"]))
        series[key] = [
            (float(row["rank_index"]), float(row["stop_iteration"]))
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
    ax.set_xlabel("Laufindex nach ansteigender Anzahl Iterationen bis zum Abbruch", fontsize=16)
    ax.set_ylabel("Anzahl Iterationen bis zum Abbruch", fontsize=16)
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
