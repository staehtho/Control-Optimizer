from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np


DEFAULT_INPUT_DIR = Path(__file__).resolve().parent / "results" / "pt2_d01_u100_convergence_runs"
DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
    / "data"
    / "pso_convergence"
    / "pt2_d01_u100_convergence_runs"
)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def to_float(value: str | None) -> float:
    if value is None:
        return math.nan
    text = str(value).strip()
    if text == "":
        return math.nan
    return float(text)


def to_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return int(float(text))


def sort_metric_rows(rows: list[dict[str, object]], metric_key: str) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            float(row[metric_key]),
            int(row["run_id"]),
        ),
    )


def add_curve_ranks(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    total = len(rows)
    ranked: list[dict[str, object]] = []
    for idx, row in enumerate(rows, start=1):
        out = dict(row)
        out["rank_index"] = idx
        out["rank_fraction"] = idx / total if total else math.nan
        ranked.append(out)
    return ranked


def build_config_lookup(manifest_rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for row in manifest_rows:
        config_id = str(row["config_id"])
        lookup[config_id] = {
            "config_id": config_id,
            "family": str(row["family"]),
            "hardness": str(row["hardness"]),
            "threshold_value": to_float(row.get("threshold_value")),
            "threshold_unit": str(row.get("threshold_unit", "")),
        }
    return lookup


def build_overview_rows(
    *,
    config_lookup: dict[str, dict[str, object]],
    run_rows_by_config: dict[str, list[dict[str, str]]],
) -> list[dict[str, object]]:
    overview: list[dict[str, object]] = []
    for config_id, config_meta in config_lookup.items():
        rows = run_rows_by_config.get(config_id, [])
        feasible_rows = [row for row in rows if to_int(row.get("feasible_found")) == 1]

        first_feasible_values = [
            to_int(row.get("first_feasible_iteration"))
            for row in feasible_rows
            if to_int(row.get("first_feasible_iteration")) is not None
        ]
        stop_iteration_values = [
            to_int(row.get("stop_iteration"))
            for row in rows
            if to_int(row.get("stop_iteration")) is not None
        ]
        feasible_cost_values = [
            to_float(row.get("final_best_feasible_cost"))
            for row in feasible_rows
            if math.isfinite(to_float(row.get("final_best_feasible_cost")))
        ]

        best_observed_feasible_cost = min(feasible_cost_values) if feasible_cost_values else math.nan

        overview.append(
            {
                **config_meta,
                "num_runs_total": len(rows),
                "num_feasible_runs": len(feasible_rows),
                "feasible_rate": (len(feasible_rows) / len(rows)) if rows else math.nan,
                "median_first_feasible_iteration": (
                    median(first_feasible_values) if first_feasible_values else math.nan
                ),
                "median_stop_iteration": median(stop_iteration_values) if stop_iteration_values else math.nan,
                "best_observed_feasible_cost": best_observed_feasible_cost,
                "median_final_best_feasible_cost": (
                    median(feasible_cost_values) if feasible_cost_values else math.nan
                ),
            }
        )
    return overview


def build_time_to_first_feasible_rows(
    *,
    config_lookup: dict[str, dict[str, object]],
    run_rows_by_config: dict[str, list[dict[str, str]]],
) -> list[dict[str, object]]:
    all_rows: list[dict[str, object]] = []
    for config_id, config_meta in config_lookup.items():
        run_rows = run_rows_by_config.get(config_id, [])
        feasible_rows = [row for row in run_rows if to_int(row.get("feasible_found")) == 1]
        curve_rows: list[dict[str, object]] = []
        for row in feasible_rows:
            metric = to_int(row.get("first_feasible_iteration"))
            if metric is None:
                continue
            curve_rows.append(
                {
                    **config_meta,
                    "run_id": to_int(row.get("run_id")),
                    "seed": to_int(row.get("seed")),
                    "time_to_first_feasible": metric,
                    "num_feasible_runs": len(feasible_rows),
                    "num_runs_total": len(run_rows),
                }
            )
        curve_rows = sort_metric_rows(curve_rows, "time_to_first_feasible")
        all_rows.extend(add_curve_ranks(curve_rows))
    return all_rows


def build_stop_iteration_rows(
    *,
    config_lookup: dict[str, dict[str, object]],
    run_rows_by_config: dict[str, list[dict[str, str]]],
) -> list[dict[str, object]]:
    all_rows: list[dict[str, object]] = []
    for config_id, config_meta in config_lookup.items():
        run_rows = run_rows_by_config.get(config_id, [])
        curve_rows: list[dict[str, object]] = []
        for row in run_rows:
            metric = to_int(row.get("stop_iteration"))
            if metric is None:
                continue
            curve_rows.append(
                {
                    **config_meta,
                    "run_id": to_int(row.get("run_id")),
                    "seed": to_int(row.get("seed")),
                    "stop_iteration": metric,
                    "feasible_found": to_int(row.get("feasible_found")),
                    "num_runs_total": len(run_rows),
                }
            )
        curve_rows = sort_metric_rows(curve_rows, "stop_iteration")
        all_rows.extend(add_curve_ranks(curve_rows))
    return all_rows


def build_relative_cost_rows(
    *,
    config_lookup: dict[str, dict[str, object]],
    run_rows_by_config: dict[str, list[dict[str, str]]],
) -> list[dict[str, object]]:
    all_rows: list[dict[str, object]] = []
    for config_id, config_meta in config_lookup.items():
        run_rows = run_rows_by_config.get(config_id, [])
        feasible_rows = [row for row in run_rows if to_int(row.get("feasible_found")) == 1]
        feasible_costs = [
            to_float(row.get("final_best_feasible_cost"))
            for row in feasible_rows
            if math.isfinite(to_float(row.get("final_best_feasible_cost")))
        ]
        if not feasible_costs:
            continue

        best_observed = min(feasible_costs)
        curve_rows: list[dict[str, object]] = []
        for row in feasible_rows:
            cost = to_float(row.get("final_best_feasible_cost"))
            if not math.isfinite(cost):
                continue
            relative = (cost - best_observed) / best_observed if best_observed != 0.0 else math.nan
            curve_rows.append(
                {
                    **config_meta,
                    "run_id": to_int(row.get("run_id")),
                    "seed": to_int(row.get("seed")),
                    "final_best_feasible_cost": cost,
                    "best_observed_feasible_cost": best_observed,
                    "relative_deviation_to_best": relative,
                    "num_feasible_runs": len(feasible_rows),
                    "num_runs_total": len(run_rows),
                }
            )
        curve_rows = sort_metric_rows(curve_rows, "relative_deviation_to_best")
        all_rows.extend(add_curve_ranks(curve_rows))
    return all_rows


def build_trace_lookup(
    iteration_rows: list[dict[str, str]],
) -> dict[tuple[str, int], dict[int, dict[str, float | bool]]]:
    trace_lookup: dict[tuple[str, int], dict[int, dict[str, float | bool]]] = defaultdict(dict)
    for row in iteration_rows:
        config_id = str(row["config_id"])
        run_id = to_int(row.get("run_id"))
        iteration = to_int(row.get("iteration"))
        if run_id is None or iteration is None:
            continue
        trace_lookup[(config_id, run_id)][iteration] = {
            "feasible_so_far": bool(to_int(row.get("feasible_so_far"))),
            "best_so_far_violation": to_float(row.get("best_so_far_violation")),
            "best_so_far_feasible_cost": to_float(row.get("best_so_far_feasible_cost")),
            "best_so_far_objective_cost": to_float(row.get("best_so_far_objective_cost")),
        }
    return trace_lookup


def build_median_violation_rows(
    *,
    config_lookup: dict[str, dict[str, object]],
    run_rows_by_config: dict[str, list[dict[str, str]]],
    trace_lookup: dict[tuple[str, int], dict[int, dict[str, float | bool]]],
) -> list[dict[str, object]]:
    output_rows: list[dict[str, object]] = []
    for config_id, config_meta in config_lookup.items():
        run_rows = run_rows_by_config.get(config_id, [])
        stop_values = [to_int(row.get("stop_iteration")) for row in run_rows if to_int(row.get("stop_iteration")) is not None]
        if not stop_values:
            continue
        max_iteration = max(stop_values)

        per_run_trace: dict[int, dict[int, dict[str, float | bool]]] = {
            to_int(row.get("run_id")): trace_lookup.get((config_id, to_int(row.get("run_id"))), {})
            for row in run_rows
            if to_int(row.get("run_id")) is not None
        }

        for iteration in range(max_iteration + 1):
            values: list[float] = []
            for row in run_rows:
                run_id = to_int(row.get("run_id"))
                stop_iteration = to_int(row.get("stop_iteration"))
                if run_id is None or stop_iteration is None:
                    continue
                run_trace = per_run_trace.get(run_id, {})
                last_known_iter = min(iteration, stop_iteration)
                while last_known_iter >= 0 and last_known_iter not in run_trace:
                    last_known_iter -= 1
                if last_known_iter < 0:
                    continue
                value = float(run_trace[last_known_iter]["best_so_far_violation"])
                if math.isfinite(value):
                    values.append(value)

            output_rows.append(
                {
                    **config_meta,
                    "iteration": iteration,
                    "median_best_so_far_violation": float(np.median(values)) if values else math.nan,
                    "num_runs_total": len(run_rows),
                    "num_runs_included": len(values),
                }
            )
    return output_rows


def build_median_feasible_cost_rows(
    *,
    config_lookup: dict[str, dict[str, object]],
    run_rows_by_config: dict[str, list[dict[str, str]]],
    trace_lookup: dict[tuple[str, int], dict[int, dict[str, float | bool]]],
) -> list[dict[str, object]]:
    output_rows: list[dict[str, object]] = []
    for config_id, config_meta in config_lookup.items():
        run_rows = run_rows_by_config.get(config_id, [])
        stop_values = [to_int(row.get("stop_iteration")) for row in run_rows if to_int(row.get("stop_iteration")) is not None]
        feasible_costs = [
            to_float(row.get("final_best_feasible_cost"))
            for row in run_rows
            if math.isfinite(to_float(row.get("final_best_feasible_cost")))
        ]
        if not stop_values:
            continue

        max_iteration = max(stop_values)
        best_observed = min(feasible_costs) if feasible_costs else math.nan

        per_run_trace: dict[int, dict[int, dict[str, float | bool]]] = {
            to_int(row.get("run_id")): trace_lookup.get((config_id, to_int(row.get("run_id"))), {})
            for row in run_rows
            if to_int(row.get("run_id")) is not None
        }

        for iteration in range(max_iteration + 1):
            values: list[float] = []
            for row in run_rows:
                run_id = to_int(row.get("run_id"))
                stop_iteration = to_int(row.get("stop_iteration"))
                if run_id is None or stop_iteration is None:
                    continue
                run_trace = per_run_trace.get(run_id, {})
                last_known_iter = min(iteration, stop_iteration)
                while last_known_iter >= 0 and last_known_iter not in run_trace:
                    last_known_iter -= 1
                if last_known_iter < 0:
                    continue
                value = float(run_trace[last_known_iter]["best_so_far_feasible_cost"])
                if math.isfinite(value):
                    values.append(value)

            median_cost = float(np.median(values)) if values else math.nan
            relative = (
                (median_cost - best_observed) / best_observed
                if values and math.isfinite(best_observed) and best_observed != 0.0
                else math.nan
            )

            output_rows.append(
                {
                    **config_meta,
                    "iteration": iteration,
                    "median_best_so_far_feasible_cost": median_cost,
                    "median_best_so_far_feasible_cost_relative": relative,
                    "best_observed_feasible_cost": best_observed,
                    "num_runs_total": len(run_rows),
                    "num_feasible_runs_included": len(values),
                }
            )
    return output_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create plot-ready CSV files for the PSO convergence study from "
            "config_manifest.csv, run_summary.csv and iteration_trace.csv."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=str(DEFAULT_INPUT_DIR),
        help=f"Directory containing convergence study result CSVs (default: {DEFAULT_INPUT_DIR}).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Target directory inside BA-Dokumentation for plot-ready CSVs (default: {DEFAULT_OUTPUT_DIR}).",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = read_csv_rows(input_dir / "config_manifest.csv")
    run_summary_rows = read_csv_rows(input_dir / "run_summary.csv")
    iteration_rows = read_csv_rows(input_dir / "iteration_trace.csv")

    config_lookup = build_config_lookup(manifest_rows)
    run_rows_by_config: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in run_summary_rows:
        run_rows_by_config[str(row["config_id"])].append(row)
    trace_lookup = build_trace_lookup(iteration_rows)

    config_overview_rows = build_overview_rows(
        config_lookup=config_lookup,
        run_rows_by_config=run_rows_by_config,
    )
    time_to_first_feasible_rows = build_time_to_first_feasible_rows(
        config_lookup=config_lookup,
        run_rows_by_config=run_rows_by_config,
    )
    stop_iteration_rows = build_stop_iteration_rows(
        config_lookup=config_lookup,
        run_rows_by_config=run_rows_by_config,
    )
    relative_cost_rows = build_relative_cost_rows(
        config_lookup=config_lookup,
        run_rows_by_config=run_rows_by_config,
    )
    median_violation_rows = build_median_violation_rows(
        config_lookup=config_lookup,
        run_rows_by_config=run_rows_by_config,
        trace_lookup=trace_lookup,
    )
    median_feasible_cost_rows = build_median_feasible_cost_rows(
        config_lookup=config_lookup,
        run_rows_by_config=run_rows_by_config,
        trace_lookup=trace_lookup,
    )

    write_csv(
        output_dir / "config_overview.csv",
        config_overview_rows,
        [
            "config_id",
            "family",
            "hardness",
            "threshold_value",
            "threshold_unit",
            "num_runs_total",
            "num_feasible_runs",
            "feasible_rate",
            "median_first_feasible_iteration",
            "median_stop_iteration",
            "best_observed_feasible_cost",
            "median_final_best_feasible_cost",
        ],
    )
    write_csv(
        output_dir / "curve_time_to_first_feasible.csv",
        time_to_first_feasible_rows,
        [
            "config_id",
            "family",
            "hardness",
            "threshold_value",
            "threshold_unit",
            "run_id",
            "seed",
            "time_to_first_feasible",
            "num_feasible_runs",
            "num_runs_total",
            "rank_index",
            "rank_fraction",
        ],
    )
    write_csv(
        output_dir / "curve_stop_iteration.csv",
        stop_iteration_rows,
        [
            "config_id",
            "family",
            "hardness",
            "threshold_value",
            "threshold_unit",
            "run_id",
            "seed",
            "stop_iteration",
            "feasible_found",
            "num_runs_total",
            "rank_index",
            "rank_fraction",
        ],
    )
    write_csv(
        output_dir / "curve_relative_final_cost.csv",
        relative_cost_rows,
        [
            "config_id",
            "family",
            "hardness",
            "threshold_value",
            "threshold_unit",
            "run_id",
            "seed",
            "final_best_feasible_cost",
            "best_observed_feasible_cost",
            "relative_deviation_to_best",
            "num_feasible_runs",
            "num_runs_total",
            "rank_index",
            "rank_fraction",
        ],
    )
    write_csv(
        output_dir / "curve_median_best_violation.csv",
        median_violation_rows,
        [
            "config_id",
            "family",
            "hardness",
            "threshold_value",
            "threshold_unit",
            "iteration",
            "median_best_so_far_violation",
            "num_runs_total",
            "num_runs_included",
        ],
    )
    write_csv(
        output_dir / "curve_median_best_feasible_cost.csv",
        median_feasible_cost_rows,
        [
            "config_id",
            "family",
            "hardness",
            "threshold_value",
            "threshold_unit",
            "iteration",
            "median_best_so_far_feasible_cost",
            "median_best_so_far_feasible_cost_relative",
            "best_observed_feasible_cost",
            "num_runs_total",
            "num_feasible_runs_included",
        ],
    )

    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print("Wrote:")
    print(f"- {output_dir / 'config_overview.csv'}")
    print(f"- {output_dir / 'curve_time_to_first_feasible.csv'}")
    print(f"- {output_dir / 'curve_stop_iteration.csv'}")
    print(f"- {output_dir / 'curve_relative_final_cost.csv'}")
    print(f"- {output_dir / 'curve_median_best_violation.csv'}")
    print(f"- {output_dir / 'curve_median_best_feasible_cost.csv'}")


if __name__ == "__main__":
    main()
