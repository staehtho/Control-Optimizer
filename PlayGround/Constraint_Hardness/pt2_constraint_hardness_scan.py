from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app_domain.controlsys import AntiWindup, MySolver, PIDClosedLoop, PerformanceIndex, Plant, PsoFunc


# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

PT2_PRESETS: dict[str, dict[str, list[float]]] = {
    "aperiodic": {
        "num": [1.0],
        "den": [1.0, 2.2, 1.0],
    },
    "oscillatory": {
        "num": [1.0],
        "den": [1.0, 0.4, 1.0],
    },
    "oscillatory_d05": {
        "num": [1.0],
        "den": [1.0, 1.0, 1.0],
    },
    "oscillatory_d01": {
        "num": [1.0],
        "den": [1.0, 0.2, 1.0],
    },
}

PLANT_PRESET = "oscillatory_d01"

CONTROL_CONSTRAINT = (-100.0, 100.0)
PID_BOUNDS = {
    "kp": (0.0, 10.0),
    "ti": (0.05, 10.0),
    "td": (0.0, 10.0),
}

TIME_CONFIG = {
    "t0": 0.0,
    "t1": 10.0,
    "dt": 1e-4,
}

TF_CONFIG = {
    "tuning_factor_n": 5.0,
    "limit_factor_k": 5.0,
    "sampling_rate_hz": None,
}

FREQ_GRID = {
    "low_exp": -5.0,
    "high_exp": 5.0,
    "points": 500,
}

TARGET_FEASIBLE_RATIOS = {
    "easy": 0.50,
    "medium": 0.20,
    "hard": 0.05,
}

SAMPLING_CONFIG = {
    "particles_per_batch": 300,
    "batches_per_point": 10,
    "initial_swarm_span": 2000,
    "seed": 12345,
}

# For overshoot / du_dt families you may want a baseline frequency guard to
# remove obviously unstable candidates from the "feasible" pool.
BASELINE_FREQUENCY_GUARD = {
    "enabled": False,
    "pm_min_deg": 0.0,
    "gm_min_db": 0.0,
    "ms_max_db": None,
}


@dataclass(frozen=True)
class SweepPoint:
    family: str
    order_value: float
    label: str
    params: dict[str, float | bool | None]


SCAN_CONFIG = {
    "pm": {"start": 0.0, "stop": 60.0, "count": 20},
    "ms": {"start": 24.0, "stop": 0.0, "count": 20},
    "overshoot": {"start": 90.0, "stop": 5.0, "count": 20},
    "du_dt": {"start": 500.0, "stop": 1.0, "count": 20},
}


def build_step_signal():
    return (
        lambda t: np.ones_like(t, dtype=np.float64),
        lambda t: np.zeros_like(t, dtype=np.float64),
        lambda t: np.zeros_like(t, dtype=np.float64),
    )


def build_pid_closed_loop() -> PIDClosedLoop:
    preset = PT2_PRESETS[PLANT_PRESET]
    plant = Plant(num=preset["num"], den=preset["den"])
    return PIDClosedLoop(
        plant,
        Kp=1.0,
        Ti=1.0,
        Td=0.0,
        Tf=0.0,
        control_constraint=list(CONTROL_CONSTRAINT),
        anti_windup_method=AntiWindup.CLAMPING,
    )


def build_pso_func(sweep_point: SweepPoint, swarm_size: int) -> PsoFunc:
    pid = build_pid_closed_loop()
    r, l, n = build_step_signal()

    use_freq_metrics = bool(sweep_point.params.get("use_freq_metrics", False))

    return PsoFunc(
        pid,
        TIME_CONFIG["t0"],
        TIME_CONFIG["t1"],
        TIME_CONFIG["dt"],
        r=r,
        l=l,
        n=n,
        solver=MySolver.RK4,
        performance_index=PerformanceIndex.ITAE,
        swarm_size=swarm_size,
        pre_compiling=False,
        use_freq_metrics=use_freq_metrics,
        tf_tuning_factor_n=TF_CONFIG["tuning_factor_n"],
        tf_limit_factor_k=TF_CONFIG["limit_factor_k"],
        sampling_rate_hz=TF_CONFIG["sampling_rate_hz"],
        freq_low_exp=FREQ_GRID["low_exp"],
        freq_high_exp=FREQ_GRID["high_exp"],
        freq_points=FREQ_GRID["points"],
        pm_min_deg=float(sweep_point.params.get("pm_min_deg", 0.0)),
        gm_min_db=float(sweep_point.params.get("gm_min_db", 0.0)),
        ms_max_db=sweep_point.params.get("ms_max_db"),
        use_overshoot_control=bool(sweep_point.params.get("use_overshoot_control", False)),
        allowed_overshoot_pct=float(sweep_point.params.get("allowed_overshoot_pct", 0.0)),
        calculate_overshoot=True,
        use_max_du_dt_constraint=bool(sweep_point.params.get("use_max_du_dt_constraint", False)),
        calculate_max_du_dt=True,
        allowed_max_du_dt=float(sweep_point.params.get("allowed_max_du_dt", 0.0)),
        du_dt_window_steps=int(sweep_point.params.get("du_dt_window_steps", 10)),
    )


def pm_sweep_points() -> list[SweepPoint]:
    values = np.linspace(
        SCAN_CONFIG["pm"]["start"],
        SCAN_CONFIG["pm"]["stop"],
        int(SCAN_CONFIG["pm"]["count"]),
        dtype=np.float64,
    )
    points: list[SweepPoint] = []

    for value in values:
        points.append(
            SweepPoint(
                family="pm",
                order_value=float(value),
                label=f"pm>={value:.1f} deg",
                params={
                    "use_freq_metrics": True,
                    "pm_min_deg": float(value),
                    "gm_min_db": 0.0,
                    "ms_max_db": None,
                    "use_overshoot_control": False,
                    "use_max_du_dt_constraint": False,
                },
            )
        )

    return points


def ms_sweep_points() -> list[SweepPoint]:
    values = np.linspace(
        SCAN_CONFIG["ms"]["start"],
        SCAN_CONFIG["ms"]["stop"],
        int(SCAN_CONFIG["ms"]["count"]),
        dtype=np.float64,
    )
    points: list[SweepPoint] = []

    for value in values:
        points.append(
            SweepPoint(
                family="ms",
                order_value=float(-value),
                label=f"Ms<={value:.1f} dB",
                params={
                    "use_freq_metrics": True,
                    "pm_min_deg": 0.0,
                    "gm_min_db": 0.0,
                    "ms_max_db": float(value),
                    "use_overshoot_control": False,
                    "use_max_du_dt_constraint": False,
                },
            )
        )

    return points


def overshoot_sweep_points() -> list[SweepPoint]:
    values = np.linspace(
        SCAN_CONFIG["overshoot"]["start"],
        SCAN_CONFIG["overshoot"]["stop"],
        int(SCAN_CONFIG["overshoot"]["count"]),
        dtype=np.float64,
    )
    points: list[SweepPoint] = []

    for value in values:
        params: dict[str, float | bool | None] = {
            "use_freq_metrics": bool(BASELINE_FREQUENCY_GUARD["enabled"]),
            "pm_min_deg": float(BASELINE_FREQUENCY_GUARD["pm_min_deg"]),
            "gm_min_db": float(BASELINE_FREQUENCY_GUARD["gm_min_db"]),
            "ms_max_db": BASELINE_FREQUENCY_GUARD["ms_max_db"],
            "use_overshoot_control": True,
            "allowed_overshoot_pct": float(value),
            "use_max_du_dt_constraint": False,
        }
        points.append(
            SweepPoint(
                family="overshoot",
                order_value=float(-value),
                label=f"overshoot<={value:.3g} %",
                params=params,
            )
        )

    return points


def du_dt_sweep_points() -> list[SweepPoint]:
    values = np.linspace(
        SCAN_CONFIG["du_dt"]["start"],
        SCAN_CONFIG["du_dt"]["stop"],
        int(SCAN_CONFIG["du_dt"]["count"]),
        dtype=np.float64,
    )
    points: list[SweepPoint] = []

    for value in values:
        params: dict[str, float | bool | None] = {
            "use_freq_metrics": bool(BASELINE_FREQUENCY_GUARD["enabled"]),
            "pm_min_deg": float(BASELINE_FREQUENCY_GUARD["pm_min_deg"]),
            "gm_min_db": float(BASELINE_FREQUENCY_GUARD["gm_min_db"]),
            "ms_max_db": BASELINE_FREQUENCY_GUARD["ms_max_db"],
            "use_overshoot_control": False,
            "use_max_du_dt_constraint": True,
            "allowed_max_du_dt": float(value),
            "du_dt_window_steps": 10,
        }
        points.append(
            SweepPoint(
                family="du_dt",
                order_value=float(-value),
                label=f"du/dt<={value:.4g}",
                params=params,
            )
        )

    return points


def build_all_sweep_points() -> list[SweepPoint]:
    return (
        pm_sweep_points()
        + ms_sweep_points()
        + overshoot_sweep_points()
        + du_dt_sweep_points()
    )


def sample_initial_particles(
    *,
    count: int,
    rng: np.random.Generator,
    initial_swarm_span: int,
) -> np.ndarray:
    lower = np.array(
        [PID_BOUNDS["kp"][0], PID_BOUNDS["ti"][0], PID_BOUNDS["td"][0]],
        dtype=np.float64,
    )
    upper = np.array(
        [PID_BOUNDS["kp"][1], PID_BOUNDS["ti"][1], PID_BOUNDS["td"][1]],
        dtype=np.float64,
    )
    step = (upper - lower) / float(initial_swarm_span)
    indices = rng.integers(0, initial_swarm_span + 1, size=(count, 3), endpoint=False)
    return lower + indices * step


def evaluate_sweep_point(sweep_point: SweepPoint) -> dict[str, float | str | int]:
    batch_size = int(SAMPLING_CONFIG["particles_per_batch"])
    batches = int(SAMPLING_CONFIG["batches_per_point"])
    initial_swarm_span = int(SAMPLING_CONFIG["initial_swarm_span"])
    seed = int(SAMPLING_CONFIG["seed"])

    feasible_ratios: list[float] = []
    violation_medians: list[float] = []
    feasible_perf_medians: list[float] = []

    obj_func = build_pso_func(sweep_point, swarm_size=batch_size)

    for batch_idx in range(batches):
        rng = np.random.default_rng(seed + 1000 * batch_idx + int(abs(1000.0 * sweep_point.order_value)))
        X = sample_initial_particles(
            count=batch_size,
            rng=rng,
            initial_swarm_span=initial_swarm_span,
        )
        result = obj_func.evaluate_candidates(X)

        feasible = np.asarray(result["feasible"], dtype=bool)
        violation = np.asarray(result["violation"], dtype=np.float64)
        perf = np.asarray(result["perf"], dtype=np.float64)

        feasible_ratio = float(np.mean(feasible))
        feasible_ratios.append(feasible_ratio)

        infeasible_mask = ~feasible
        if np.any(infeasible_mask):
            violation_medians.append(float(np.nanmedian(violation[infeasible_mask])))
        else:
            violation_medians.append(0.0)

        if np.any(feasible):
            feasible_perf_medians.append(float(np.nanmedian(perf[feasible])))
        else:
            feasible_perf_medians.append(math.nan)

    row: dict[str, float | str | int] = {
        "family": sweep_point.family,
        "order_value": sweep_point.order_value,
        "label": sweep_point.label,
        "batches": batches,
        "particles_per_batch": batch_size,
        "mean_feasible_ratio": float(mean(feasible_ratios)),
        "std_feasible_ratio": float(pstdev(feasible_ratios)) if len(feasible_ratios) > 1 else 0.0,
        "mean_infeasible_violation_median": float(mean(violation_medians)),
        "mean_feasible_perf_median": (
            float(np.nanmean(np.asarray(feasible_perf_medians, dtype=np.float64)))
            if np.any(np.isfinite(feasible_perf_medians))
            else math.nan
        ),
    }

    for key, value in sweep_point.params.items():
        row[key] = value if value is not None else ""

    return row


def choose_target_rows(rows: list[dict[str, float | str | int]]) -> list[dict[str, float | str | int]]:
    selected: list[dict[str, float | str | int]] = []
    for family in ("pm", "ms", "overshoot", "du_dt"):
        family_rows = [row for row in rows if row["family"] == family]
        for hardness_label, target_ratio in TARGET_FEASIBLE_RATIOS.items():
            best_row = min(
                family_rows,
                key=lambda row: abs(float(row["mean_feasible_ratio"]) - target_ratio),
            )
            summary = dict(best_row)
            summary["hardness"] = hardness_label
            summary["target_feasible_ratio"] = target_ratio
            summary["target_distance"] = abs(float(best_row["mean_feasible_ratio"]) - target_ratio)
            selected.append(summary)
    return selected


def write_csv(path: Path, rows: list[dict[str, float | str | int]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_plot_ready_rows(
    sweep_rows: list[dict[str, float | str | int]],
    summary_rows: list[dict[str, float | str | int]],
) -> list[dict[str, float | str | int]]:
    summary_index: dict[tuple[str, str], dict[str, float | str | int]] = {}
    for row in summary_rows:
        family = str(row["family"])
        label = str(row["label"])
        summary_index[(family, label)] = row

    family_meta = {
        "pm": {
            "family_label": "Phasenreserve PM",
            "threshold_column": "pm_min_deg",
            "threshold_unit": "deg",
            "constraint_type": "minimum",
        },
        "ms": {
            "family_label": "Stabilität Ms",
            "threshold_column": "ms_max_db",
            "threshold_unit": "dB",
            "constraint_type": "maximum",
        },
        "overshoot": {
            "family_label": "Maximales Überschwingen",
            "threshold_column": "allowed_overshoot_pct",
            "threshold_unit": "%",
            "constraint_type": "maximum",
        },
        "du_dt": {
            "family_label": "Maximale Stellrate du/dt",
            "threshold_column": "allowed_max_du_dt",
            "threshold_unit": "1/s",
            "constraint_type": "maximum",
        },
    }

    plot_rows: list[dict[str, float | str | int]] = []
    for row in sweep_rows:
        family = str(row["family"])
        meta = family_meta[family]
        threshold_col = str(meta["threshold_column"])
        threshold_raw = row.get(threshold_col, "")
        threshold_value = float(threshold_raw) if threshold_raw != "" else math.nan
        summary_match = summary_index.get((family, str(row["label"])))

        plot_row: dict[str, float | str | int] = {
            "family": family,
            "family_label": str(meta["family_label"]),
            "label": str(row["label"]),
            "threshold_value": threshold_value,
            "threshold_unit": str(meta["threshold_unit"]),
            "constraint_type": str(meta["constraint_type"]),
            "mean_feasible_ratio": float(row["mean_feasible_ratio"]),
            "mean_feasible_percent": 100.0 * float(row["mean_feasible_ratio"]),
            "std_feasible_ratio": float(row["std_feasible_ratio"]),
            "std_feasible_percent": 100.0 * float(row["std_feasible_ratio"]),
            "selected_hardness": str(summary_match["hardness"]) if summary_match else "",
            "selected_target_ratio": (
                float(summary_match["target_feasible_ratio"]) if summary_match else math.nan
            ),
            "selected_target_percent": (
                100.0 * float(summary_match["target_feasible_ratio"]) if summary_match else math.nan
            ),
        }
        plot_rows.append(plot_row)

    plot_rows.sort(
        key=lambda r: (
            str(r["family"]),
            float(r["threshold_value"]) if math.isfinite(float(r["threshold_value"])) else float("inf"),
        )
    )
    return plot_rows


def build_overlay_ready_rows(
    plot_rows: list[dict[str, float | str | int]],
) -> list[dict[str, float | str | int]]:
    overlay_rows: list[dict[str, float | str | int]] = []
    families = sorted({str(row["family"]) for row in plot_rows})

    for family in families:
        family_rows = [row for row in plot_rows if str(row["family"]) == family]
        family_rows = sorted(family_rows, key=lambda row: float(row["threshold_value"]))

        x_raw = np.array([float(row["threshold_value"]) for row in family_rows], dtype=np.float64)
        x_min = float(np.min(x_raw))
        x_max = float(np.max(x_raw))
        x_span = x_max - x_min

        for idx, row in enumerate(family_rows):
            x_value = float(row["threshold_value"])
            if x_span > 0.0:
                severity = (x_value - x_min) / x_span
            else:
                severity = 0.0

            if str(row["constraint_type"]) == "maximum":
                severity = 1.0 - severity

            overlay_rows.append(
                {
                    "family": str(row["family"]),
                    "family_label": str(row["family_label"]),
                    "threshold_value": x_value,
                    "threshold_unit": str(row["threshold_unit"]),
                    "constraint_type": str(row["constraint_type"]),
                    "severity_norm": float(severity),
                    "severity_percent": 100.0 * float(severity),
                    "series_index": idx,
                    "mean_feasible_ratio": float(row["mean_feasible_ratio"]),
                    "mean_feasible_percent": float(row["mean_feasible_percent"]),
                    "std_feasible_ratio": float(row["std_feasible_ratio"]),
                    "std_feasible_percent": float(row["std_feasible_percent"]),
                    "selected_hardness": str(row["selected_hardness"]),
                    "label": str(row["label"]),
                }
            )

    overlay_rows.sort(key=lambda row: (str(row["family"]), float(row["severity_norm"])))
    return overlay_rows


def _format_threshold_label(value: float, unit: str) -> str:
    if unit == "deg":
        return f"{value:.0f}°"
    if unit == "dB":
        if abs(value - round(value)) < 1e-9:
            return f"{value:.0f} dB"
        return f"{value:.2f} dB"
    if unit == "%":
        if abs(value - round(value)) < 1e-9:
            return f"{value:.0f} %"
        return f"{value:.1f} %"
    if value >= 100.0:
        return f"{value:.0f}"
    if value >= 10.0:
        return f"{value:.2f}"
    if value >= 1.0:
        return f"{value:.3g}"
    return f"{value:.3g}"


def _format_threshold_label_clean(value: float, unit: str) -> str:
    if unit == "deg":
        return f"{value:.0f}°"
    if unit == "dB":
        if abs(value - round(value)) < 1e-9:
            return f"{value:.0f} dB"
        return f"{value:.2f} dB"
    if unit == "%":
        if abs(value - round(value)) < 1e-9:
            return f"{value:.0f} %"
        return f"{value:.1f} %"
    if value >= 100.0:
        return f"{value:.0f}"
    if value >= 10.0:
        return f"{value:.2f}"
    if value >= 1.0:
        return f"{value:.3g}"
    return f"{value:.3g}"


def build_categorical_ready_rows(
    plot_rows: list[dict[str, float | str | int]],
) -> list[dict[str, float | str | int]]:
    categorical_rows: list[dict[str, float | str | int]] = []
    families = ["pm", "ms", "overshoot", "du_dt"]
    gap = 2
    x_cursor = 0

    for family in families:
        family_rows = [row for row in plot_rows if str(row["family"]) == family]
        if not family_rows:
            continue

        family_rows = sorted(
            family_rows,
            key=lambda row: float(row["threshold_value"]),
            reverse=(str(family_rows[0]["constraint_type"]) == "maximum"),
        )

        block_start = x_cursor
        for local_idx, row in enumerate(family_rows):
            x_position = x_cursor + local_idx
            threshold_value = float(row["threshold_value"])
            threshold_unit = str(row["threshold_unit"])
            categorical_rows.append(
                {
                    "family": str(row["family"]),
                    "family_label": str(row["family_label"]),
                    "x_position": x_position,
                    "block_start": block_start,
                    "block_end": block_start + len(family_rows) - 1,
                    "block_center": block_start + 0.5 * (len(family_rows) - 1),
                    "threshold_value": threshold_value,
                    "threshold_unit": threshold_unit,
                    "x_label": _format_threshold_label(threshold_value, threshold_unit),
                    "mean_feasible_ratio": float(row["mean_feasible_ratio"]),
                    "mean_feasible_percent": float(row["mean_feasible_percent"]),
                    "std_feasible_ratio": float(row["std_feasible_ratio"]),
                    "std_feasible_percent": float(row["std_feasible_percent"]),
                    "selected_hardness": str(row["selected_hardness"]),
                    "label": str(row["label"]),
                }
            )

        x_cursor += len(family_rows) + gap

    return categorical_rows


def build_multi_axis_ready_rows(
    plot_rows: list[dict[str, float | str | int]],
) -> list[dict[str, float | str | int]]:
    multi_axis_rows: list[dict[str, float | str | int]] = []
    families = ["pm", "ms", "overshoot", "du_dt"]

    for family in families:
        family_rows = [row for row in plot_rows if str(row["family"]) == family]
        if not family_rows:
            continue

        family_rows = sorted(
            family_rows,
            key=lambda row: float(row["threshold_value"]),
            reverse=(str(family_rows[0]["constraint_type"]) == "maximum"),
        )

        for local_idx, row in enumerate(family_rows):
            threshold_value = float(row["threshold_value"])
            threshold_unit = str(row["threshold_unit"])
            multi_axis_rows.append(
                {
                    "family": str(row["family"]),
                    "family_label": str(row["family_label"]),
                    "x_position": local_idx,
                    "threshold_value": threshold_value,
                    "threshold_unit": threshold_unit,
                    "x_label": _format_threshold_label(threshold_value, threshold_unit),
                    "mean_feasible_ratio": float(row["mean_feasible_ratio"]),
                    "mean_feasible_percent": float(row["mean_feasible_percent"]),
                    "std_feasible_ratio": float(row["std_feasible_ratio"]),
                    "std_feasible_percent": float(row["std_feasible_percent"]),
                    "selected_hardness": str(row["selected_hardness"]),
                    "label": str(row["label"]),
                }
            )

    return multi_axis_rows


def build_stacked_label_ready_rows(
    plot_rows: list[dict[str, float | str | int]],
) -> list[dict[str, float | str | int]]:
    families = ["pm", "ms", "overshoot", "du_dt"]
    family_rows_map: dict[str, list[dict[str, float | str | int]]] = {}

    for family in families:
        family_rows = [row for row in plot_rows if str(row["family"]) == family]
        family_rows = sorted(
            family_rows,
            key=lambda row: float(row["threshold_value"]),
            reverse=(str(family_rows[0]["constraint_type"]) == "maximum"),
        )
        family_rows_map[family] = family_rows

    point_count = min(len(rows) for rows in family_rows_map.values())
    stacked_rows: list[dict[str, float | str | int]] = []

    for idx in range(point_count):
        pm_row = family_rows_map["pm"][idx]
        ms_row = family_rows_map["ms"][idx]
        overshoot_row = family_rows_map["overshoot"][idx]
        du_dt_row = family_rows_map["du_dt"][idx]

        x_label = "\n".join(
            [
                f"PM { _format_threshold_label_clean(float(pm_row['threshold_value']), str(pm_row['threshold_unit'])) }",
                f"Ms { _format_threshold_label_clean(float(ms_row['threshold_value']), str(ms_row['threshold_unit'])) }",
                f'ÜS { _format_threshold_label_clean(float(overshoot_row["threshold_value"]), str(overshoot_row["threshold_unit"])) }',
                f'du/dt { _format_threshold_label_clean(float(du_dt_row["threshold_value"]), str(du_dt_row["threshold_unit"])) }',
            ]
        )

        stacked_rows.append(
            {
                "x_position": idx,
                "x_label": x_label,
                "pm_threshold_value": float(pm_row["threshold_value"]),
                "pm_label": _format_threshold_label_clean(float(pm_row["threshold_value"]), str(pm_row["threshold_unit"])),
                "pm_mean_feasible_ratio": float(pm_row["mean_feasible_ratio"]),
                "pm_std_feasible_ratio": float(pm_row["std_feasible_ratio"]),
                "ms_threshold_value": float(ms_row["threshold_value"]),
                "ms_label": _format_threshold_label_clean(float(ms_row["threshold_value"]), str(ms_row["threshold_unit"])),
                "ms_mean_feasible_ratio": float(ms_row["mean_feasible_ratio"]),
                "ms_std_feasible_ratio": float(ms_row["std_feasible_ratio"]),
                "overshoot_threshold_value": float(overshoot_row["threshold_value"]),
                "overshoot_label": _format_threshold_label_clean(
                    float(overshoot_row["threshold_value"]), str(overshoot_row["threshold_unit"])
                ),
                "overshoot_mean_feasible_ratio": float(overshoot_row["mean_feasible_ratio"]),
                "overshoot_std_feasible_ratio": float(overshoot_row["std_feasible_ratio"]),
                "du_dt_threshold_value": float(du_dt_row["threshold_value"]),
                "du_dt_label": _format_threshold_label_clean(float(du_dt_row["threshold_value"]), str(du_dt_row["threshold_unit"])),
                "du_dt_mean_feasible_ratio": float(du_dt_row["mean_feasible_ratio"]),
                "du_dt_std_feasible_ratio": float(du_dt_row["std_feasible_ratio"]),
            }
        )

    return stacked_rows


def try_create_combined_plot(
    plot_rows: list[dict[str, float | str | int]],
    out_dir: Path,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping combined plot.")
        return

    families = ["pm", "ms", "overshoot", "du_dt"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.2), sharey=True)
    axes_list = list(axes.flat)

    for idx, family in enumerate(families):
        ax = axes_list[idx]
        family_rows = [row for row in plot_rows if row["family"] == family]
        x = np.array([float(row["threshold_value"]) for row in family_rows], dtype=np.float64)
        y = np.array([float(row["mean_feasible_ratio"]) for row in family_rows], dtype=np.float64)
        yerr = np.array([float(row["std_feasible_ratio"]) for row in family_rows], dtype=np.float64)

        ax.errorbar(x, y, yerr=yerr, fmt="-o", linewidth=1.4, markersize=3.5, capsize=2.5)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.3)
        ax.set_title(str(family_rows[0]["family_label"]))
        ax.set_xlabel(f"Schwellenwert [{family_rows[0]['threshold_unit']}]")
        if idx % 2 == 0:
            ax.set_ylabel("Feasible-Anteil")

        if str(family_rows[0]["constraint_type"]) == "maximum":
            ax.invert_xaxis()

        for hardness_name, target_ratio in TARGET_FEASIBLE_RATIOS.items():
            ax.axhline(target_ratio, linestyle="--", linewidth=0.9, color="gray", alpha=0.7)

        for row in family_rows:
            hardness = str(row["selected_hardness"])
            if not hardness:
                continue
            ax.scatter(
                [float(row["threshold_value"])],
                [float(row["mean_feasible_ratio"])],
                s=36,
                zorder=5,
                label=hardness,
            )

    handles, labels = axes_list[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)

    fig.suptitle(f"{PLANT_PRESET} | Nebenbedingungen und Feasible-Anteil", y=0.995)
    fig.tight_layout(rect=(0, 0.04, 1, 0.98))
    fig.savefig(out_dir / "constraint_hardness_combined.png", dpi=180)
    plt.close(fig)


def try_create_overlay_plot(
    overlay_rows: list[dict[str, float | str | int]],
    out_dir: Path,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping overlay plot.")
        return

    families = ["pm", "ms", "overshoot", "du_dt"]
    colors = {
        "pm": "#1f77b4",
        "ms": "#d62728",
        "overshoot": "#2ca02c",
        "du_dt": "#ff7f0e",
    }

    fig, ax = plt.subplots(figsize=(9.5, 5.8))

    for family in families:
        family_rows = [row for row in overlay_rows if str(row["family"]) == family]
        if not family_rows:
            continue

        x = np.array([float(row["severity_norm"]) for row in family_rows], dtype=np.float64)
        y = np.array([float(row["mean_feasible_ratio"]) for row in family_rows], dtype=np.float64)
        yerr = np.array([float(row["std_feasible_ratio"]) for row in family_rows], dtype=np.float64)

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            fmt="-o",
            linewidth=1.5,
            markersize=3.5,
            capsize=2.5,
            color=colors.get(family),
            label=str(family_rows[0]["family_label"]),
        )

        for row in family_rows:
            hardness = str(row["selected_hardness"])
            if not hardness:
                continue
            ax.scatter(
                [float(row["severity_norm"])],
                [float(row["mean_feasible_ratio"])],
                s=44,
                color=colors.get(family),
                zorder=5,
            )

    for hardness_name, target_ratio in TARGET_FEASIBLE_RATIOS.items():
        ax.axhline(target_ratio, linestyle="--", linewidth=0.9, color="gray", alpha=0.7)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Normierte Härte innerhalb der jeweiligen Nebenbedingung")
    ax.set_ylabel("Feasible-Anteil")
    ax.set_title(f"{PLANT_PRESET} | Alle Nebenbedingungen in einem Plot")
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(out_dir / "constraint_hardness_overlay.png", dpi=180)
    plt.close(fig)


def try_create_categorical_overlay_plot(
    categorical_rows: list[dict[str, float | str | int]],
    out_dir: Path,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping categorical overlay plot.")
        return

    families = ["pm", "ms", "overshoot", "du_dt"]
    colors = {
        "pm": "#1f77b4",
        "ms": "#d62728",
        "overshoot": "#2ca02c",
        "du_dt": "#ff7f0e",
    }

    fig, ax = plt.subplots(figsize=(13, 6.4))

    xticks: list[float] = []
    xticklabels: list[str] = []

    for family in families:
        family_rows = [row for row in categorical_rows if str(row["family"]) == family]
        if not family_rows:
            continue

        x = np.array([float(row["x_position"]) for row in family_rows], dtype=np.float64)
        y = np.array([float(row["mean_feasible_ratio"]) for row in family_rows], dtype=np.float64)
        yerr = np.array([float(row["std_feasible_ratio"]) for row in family_rows], dtype=np.float64)

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            fmt="-o",
            linewidth=1.5,
            markersize=3.5,
            capsize=2.5,
            color=colors.get(family),
            label=str(family_rows[0]["family_label"]),
        )

        for row in family_rows:
            xticks.append(float(row["x_position"]))
            xticklabels.append(str(row["x_label"]))
            hardness = str(row["selected_hardness"])
            if hardness:
                ax.scatter(
                    [float(row["x_position"])],
                    [float(row["mean_feasible_ratio"])],
                    s=46,
                    color=colors.get(family),
                    zorder=5,
                )

        block_start = float(family_rows[0]["block_start"])
        block_end = float(family_rows[0]["block_end"])
        block_center = float(family_rows[0]["block_center"])
        ax.text(
            block_center,
            -0.16,
            str(family_rows[0]["family_label"]),
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
        )
        ax.axvline(block_end + 1.0, color="lightgray", linewidth=0.8, alpha=0.8)

    for hardness_name, target_ratio in TARGET_FEASIBLE_RATIOS.items():
        ax.axhline(target_ratio, linestyle="--", linewidth=0.9, color="gray", alpha=0.7)

    ax.set_ylim(-0.02, 1.02)
    ax.set_ylabel("Feasible-Anteil")
    ax.set_xlabel("Schwellenwerte der Nebenbedingungen")
    ax.set_title(f"{PLANT_PRESET} | Alle Nebenbedingungen in einem Plot")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, rotation=65, ha="right")
    ax.legend(frameon=False, loc="upper right")

    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out_dir / "constraint_hardness_categorical_overlay.png", dpi=180)
    plt.close(fig)


def try_create_multi_axis_overlay_plot(
    multi_axis_rows: list[dict[str, float | str | int]],
    out_dir: Path,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping multi-axis overlay plot.")
        return

    families = ["pm", "ms", "overshoot", "du_dt"]
    colors = {
        "pm": "#1f77b4",
        "ms": "#d62728",
        "overshoot": "#2ca02c",
        "du_dt": "#ff7f0e",
    }

    fig, ax = plt.subplots(figsize=(14, 8.6))

    max_points = max(
        len([row for row in multi_axis_rows if str(row["family"]) == family]) for family in families
    )
    x_positions = np.arange(max_points, dtype=np.float64)

    for family in families:
        family_rows = [row for row in multi_axis_rows if str(row["family"]) == family]
        if not family_rows:
            continue

        x = np.array([float(row["x_position"]) for row in family_rows], dtype=np.float64)
        y = np.array([float(row["mean_feasible_ratio"]) for row in family_rows], dtype=np.float64)
        yerr = np.array([float(row["std_feasible_ratio"]) for row in family_rows], dtype=np.float64)

        ax.errorbar(
            x,
            y,
            yerr=yerr,
            fmt="-o",
            linewidth=1.6,
            markersize=3.8,
            capsize=2.5,
            color=colors[family],
            label=str(family_rows[0]["family_label"]),
        )

        for row in family_rows:
            if not str(row["selected_hardness"]):
                continue
            ax.scatter(
                [float(row["x_position"])],
                [float(row["mean_feasible_ratio"])],
                s=48,
                color=colors[family],
                zorder=5,
            )

    for hardness_name, target_ratio in TARGET_FEASIBLE_RATIOS.items():
        ax.axhline(target_ratio, linestyle="--", linewidth=0.9, color="gray", alpha=0.7)

    ax.set_xlim(-0.2, max_points - 0.8)
    ax.set_ylim(-0.02, 1.02)
    ax.set_ylabel("Feasible-Anteil")
    ax.set_title(f"{PLANT_PRESET} | Overlay mit vier x-Achsen")
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.legend(frameon=False, loc="upper right")

    axis_offsets = [0, 26, 52, 78]
    for idx, family in enumerate(families):
        family_rows = [row for row in multi_axis_rows if str(row["family"]) == family]
        if not family_rows:
            continue

        axis = ax.twiny()
        axis.set_xlim(ax.get_xlim())
        axis.xaxis.set_ticks_position("bottom")
        axis.xaxis.set_label_position("bottom")
        axis.spines["top"].set_visible(False)
        axis.spines["bottom"].set_position(("outward", axis_offsets[idx]))
        axis.spines["bottom"].set_color(colors[family])
        axis.tick_params(axis="x", colors=colors[family], labelsize=7, pad=1, length=3)
        axis.set_xticks(x_positions)
        axis.set_xticklabels([str(row["x_label"]) for row in family_rows], rotation=55, ha="right")
        axis.set_xlabel(
            f"{family_rows[0]['family_label']} [{family_rows[0]['threshold_unit']}]",
            color=colors[family],
            labelpad=8,
        )

    fig.tight_layout(rect=(0, 0.18, 1, 1))
    fig.savefig(out_dir / "constraint_hardness_overlay_multi_x.png", dpi=180)
    plt.close(fig)


def try_create_stacked_label_overlay_plot(
    stacked_rows: list[dict[str, float | str | int]],
    out_dir: Path,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping stacked-label overlay plot.")
        return

    colors = {
        "pm": "#1f77b4",
        "ms": "#d62728",
        "overshoot": "#2ca02c",
        "du_dt": "#ff7f0e",
    }
    labels = {
        "pm": "Phasenreserve PM",
        "ms": r"Stabilität $M_s$",
        "overshoot": "Maximales Überschwingen",
        "du_dt": r"Maximale Stellrate $\mathrm{d}u/\mathrm{d}t$",
    }

    x = np.array([float(row["x_position"]) for row in stacked_rows], dtype=np.float64)
    fig, ax = plt.subplots(figsize=(15.5, 7.8))

    for family in ("pm", "ms", "overshoot", "du_dt"):
        y = np.array([float(row[f"{family}_mean_feasible_ratio"]) for row in stacked_rows], dtype=np.float64)
        yerr = np.array([float(row[f"{family}_std_feasible_ratio"]) for row in stacked_rows], dtype=np.float64)
        ax.errorbar(
            x,
            y,
            yerr=yerr,
            fmt="-o",
            linewidth=1.6,
            markersize=3.8,
            capsize=2.5,
            color=colors[family],
            label=labels[family],
        )

    for hardness_name, target_ratio in TARGET_FEASIBLE_RATIOS.items():
        ax.axhline(target_ratio, linestyle="--", linewidth=0.9, color="gray", alpha=0.7)

    tick_indices = np.linspace(0, len(stacked_rows) - 1, 4, dtype=int)
    tick_indices = np.unique(tick_indices)
    tick_positions = x[tick_indices]
    tick_labels = [str(stacked_rows[idx]["x_label"]) for idx in tick_indices]

    ax.set_xlim(-0.4, float(len(stacked_rows)) - 0.6)
    ax.set_ylim(-0.02, 1.02)
    ax.set_ylabel("Anteil zulässiger Initialpartikel", fontsize=13)
    ax.set_xlabel("Schwellenwerte je Stützstelle", fontsize=13, labelpad=8)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.legend(frameon=False, loc="upper right")

    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.savefig(out_dir / "constraint_hardness_overlay_stacked_labels.png", dpi=180)
    plt.close(fig)


def try_create_plot(rows: list[dict[str, float | str | int]], out_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping plots.")
        return

    for family in ("pm", "ms", "overshoot", "du_dt"):
        family_rows = sorted(
            (row for row in rows if row["family"] == family),
            key=lambda row: float(row["order_value"]),
        )
        x = np.arange(len(family_rows))
        y = np.array([float(row["mean_feasible_ratio"]) for row in family_rows], dtype=np.float64)
        yerr = np.array([float(row["std_feasible_ratio"]) for row in family_rows], dtype=np.float64)

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.errorbar(x, y, yerr=yerr, fmt="-o", linewidth=1.5, markersize=4, capsize=3)
        ax.set_ylim(-0.02, 1.02)
        ax.set_ylabel("Feasible ratio")
        ax.set_xlabel("Sweep index")
        ax.set_title(f"{PLANT_PRESET} PT2 | {family} constraint family")
        ax.grid(True, alpha=0.3)

        tick_step = max(1, len(family_rows) // 8)
        tick_positions = x[::tick_step]
        tick_labels = [family_rows[idx]["label"] for idx in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=25, ha="right")

        for hardness_name, target_ratio in TARGET_FEASIBLE_RATIOS.items():
            ax.axhline(target_ratio, linestyle="--", linewidth=1.0, label=f"{hardness_name}: {target_ratio:.0%}")

        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / f"{family}_feasible_ratio.png", dpi=150)
        plt.close(fig)


def print_summary(
    summary_rows: list[dict[str, float | str | int]],
    sweep_rows: list[dict[str, float | str | int]],
) -> None:
    print()
    print(f"PT2 preset: {PLANT_PRESET}")
    print(f"Plant numerator: {PT2_PRESETS[PLANT_PRESET]['num']}")
    print(f"Plant denominator: {PT2_PRESETS[PLANT_PRESET]['den']}")
    print(f"Control constraint: {CONTROL_CONSTRAINT}")
    print(f"PID bounds: {PID_BOUNDS}")
    print()
    print("Observed feasible-ratio span per family:")
    for family in ("pm", "ms", "overshoot", "du_dt"):
        family_rows = [row for row in sweep_rows if row["family"] == family]
        if not family_rows:
            continue
        feasible_values = [float(row["mean_feasible_ratio"]) for row in family_rows]
        print(f"- {family:10s}: min={min(feasible_values):.1%}, max={max(feasible_values):.1%}")
    print()
    print("Suggested hardness points based on initial feasible ratio:")

    for row in summary_rows:
        print(
            f"- {row['family']:10s} | {str(row['hardness']):6s} | "
            f"target={float(row['target_feasible_ratio']):.0%} | "
            f"observed={float(row['mean_feasible_ratio']):.1%} | "
            f"{row['label']}"
        )


def main(output_subdir: str | None = None) -> None:
    result_dir_name = f"{PLANT_PRESET}_u100" if output_subdir is None else str(output_subdir)
    out_dir = Path(__file__).resolve().parent / "results" / result_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | str | int]] = []
    sweep_points = build_all_sweep_points()

    print("Scanning PT2 constraint hardness from initial particle feasibility...")
    print(f"Preset: {PLANT_PRESET}")
    print(f"Sweep points: {len(sweep_points)}")
    print(
        "Sampling per point: "
        f"{SAMPLING_CONFIG['batches_per_point']} batches x "
        f"{SAMPLING_CONFIG['particles_per_batch']} particles"
    )

    for idx, sweep_point in enumerate(sweep_points, start=1):
        print(f"[{idx:02d}/{len(sweep_points):02d}] {sweep_point.family}: {sweep_point.label}")
        rows.append(evaluate_sweep_point(sweep_point))

    summary_rows = choose_target_rows(rows)
    plot_rows = build_plot_ready_rows(rows, summary_rows)
    overlay_rows = build_overlay_ready_rows(plot_rows)
    categorical_rows = build_categorical_ready_rows(plot_rows)
    multi_axis_rows = build_multi_axis_ready_rows(plot_rows)
    stacked_rows = build_stacked_label_ready_rows(plot_rows)

    write_csv(out_dir / "pt2_constraint_hardness_sweep.csv", rows)
    write_csv(out_dir / "pt2_constraint_hardness_summary.csv", summary_rows)
    write_csv(out_dir / "pt2_constraint_hardness_plot_ready.csv", plot_rows)
    write_csv(out_dir / "pt2_constraint_hardness_overlay_ready.csv", overlay_rows)
    write_csv(out_dir / "pt2_constraint_hardness_categorical_ready.csv", categorical_rows)
    write_csv(out_dir / "pt2_constraint_hardness_multi_axis_ready.csv", multi_axis_rows)
    write_csv(out_dir / "pt2_constraint_hardness_stacked_label_ready.csv", stacked_rows)
    try_create_plot(rows, out_dir)
    try_create_combined_plot(plot_rows, out_dir)
    try_create_overlay_plot(overlay_rows, out_dir)
    try_create_categorical_overlay_plot(categorical_rows, out_dir)
    try_create_multi_axis_overlay_plot(multi_axis_rows, out_dir)
    try_create_stacked_label_overlay_plot(stacked_rows, out_dir)
    print_summary(summary_rows, rows)

    print()
    print(f"Wrote sweep data to: {out_dir / 'pt2_constraint_hardness_sweep.csv'}")
    print(f"Wrote summary to:    {out_dir / 'pt2_constraint_hardness_summary.csv'}")
    print(f"Wrote plot data to:  {out_dir / 'pt2_constraint_hardness_plot_ready.csv'}")
    print(f"Wrote overlay data to: {out_dir / 'pt2_constraint_hardness_overlay_ready.csv'}")
    print(f"Wrote categorical plot data to: {out_dir / 'pt2_constraint_hardness_categorical_ready.csv'}")
    print(f"Wrote multi-axis plot data to: {out_dir / 'pt2_constraint_hardness_multi_axis_ready.csv'}")
    print(f"Wrote stacked-label plot data to: {out_dir / 'pt2_constraint_hardness_stacked_label_ready.csv'}")


if __name__ == "__main__":
    main()
