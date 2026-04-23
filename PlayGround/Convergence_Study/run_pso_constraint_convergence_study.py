from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app_domain.PSO import Swarm
from app_domain.controlsys import (
    AntiWindup,
    MySolver,
    PIDClosedLoop,
    PerformanceIndex,
    Plant,
)
from app_domain.pso_objective import PsoFunc, compute_effective_tf_report


# ---------------------------------------------------------------------------
# Study configuration
# ---------------------------------------------------------------------------

PLANT_NUM = [1.0]
PLANT_DEN = [1.0, 0.2, 1.0]

TIME_CONFIG = {
    "t0": 0.0,
    "t1": 10.0,
    "dt": 1e-4,
}

PID_BOUNDS = {
    "kp": (0.0, 10.0),
    "ti": (0.05, 10.0),
    "td": (0.0, 10.0),
}

CONTROL_CONSTRAINT = (-100.0, 100.0)
ANTI_WINDUP = AntiWindup.CLAMPING
PERFORMANCE_INDEX = PerformanceIndex.ITAE

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

PSO_CONFIG = {
    "swarm_size": 40,
    "max_iter": 100,
    "randomness": 1.0,
    "u1": 1.49,
    "u2": 1.49,
    "initial_range": (0.1, 1.1),
    "initial_swarm_span": 2000,
    "min_neighbors_fraction": 0.25,
    "max_stall": 15,
    "stall_windows_required": 3,
    "space_factor": 0.001,
    "convergence_factor": 1e-2,
}

DEFAULT_RUNS = 100
DEFAULT_BASE_SEED = 20260413


@dataclass(frozen=True)
class ConstraintConfig:
    config_id: str
    family: str
    hardness: str
    threshold_value: float
    threshold_unit: str
    use_freq_metrics: bool
    pm_min_deg: float
    gm_min_db: float
    ms_max_db: float | None
    use_overshoot_control: bool
    allowed_overshoot_pct: float
    use_max_du_dt_constraint: bool
    allowed_max_du_dt: float
    du_dt_window_steps: int = 10


REFERENCE_CONFIG = ConstraintConfig(
    "reference_unconstrained",
    "reference",
    "unconstrained",
    0.0,
    "-",
    False,
    0.0,
    0.0,
    None,
    False,
    0.0,
    False,
    0.0,
)


CONSTRAINT_CONFIGS: list[ConstraintConfig] = [
    ConstraintConfig("pm_easy", "pm", "easy", 11.7, "deg", True, 11.7, 0.0, None, False, 0.0, False, 0.0),
    ConstraintConfig("pm_medium", "pm", "medium", 25.9, "deg", True, 25.9, 0.0, None, False, 0.0, False, 0.0),
    ConstraintConfig("pm_hard", "pm", "hard", 46.2, "deg", True, 46.2, 0.0, None, False, 0.0, False, 0.0),
    ConstraintConfig("ms_easy", "ms", "easy", 13.7, "dB", True, 0.0, 0.0, 13.7, False, 0.0, False, 0.0),
    ConstraintConfig("ms_medium", "ms", "medium", 7.5, "dB", True, 0.0, 0.0, 7.5, False, 0.0, False, 0.0),
    ConstraintConfig("ms_hard", "ms", "hard", 3.1, "dB", True, 0.0, 0.0, 3.1, False, 0.0, False, 0.0),
    ConstraintConfig("overshoot_easy", "overshoot", "easy", 64.9, "%", False, 0.0, 0.0, None, True, 64.9, False, 0.0),
    ConstraintConfig("overshoot_medium", "overshoot", "medium", 31.6, "%", False, 0.0, 0.0, None, True, 31.6, False, 0.0),
    ConstraintConfig("overshoot_hard", "overshoot", "hard", 5.0, "%", False, 0.0, 0.0, None, True, 5.0, False, 0.0),
    ConstraintConfig("du_dt_easy", "du_dt", "easy", 159.4, "1/s", False, 0.0, 0.0, None, False, 0.0, True, 159.4),
    ConstraintConfig("du_dt_medium", "du_dt", "medium", 41.0, "1/s", False, 0.0, 0.0, None, False, 0.0, True, 41.0),
    ConstraintConfig("du_dt_hard", "du_dt", "hard", 7.5, "1/s", False, 0.0, 0.0, None, False, 0.0, True, 7.5),
]

ALL_CONFIGS: list[ConstraintConfig] = [REFERENCE_CONFIG, *CONSTRAINT_CONFIGS]


def build_step_signal() -> tuple[Callable[[np.ndarray], np.ndarray], ...]:
    return (
        lambda t: np.ones_like(t, dtype=np.float64),
        lambda t: np.zeros_like(t, dtype=np.float64),
        lambda t: np.zeros_like(t, dtype=np.float64),
    )


def build_pid_closed_loop() -> PIDClosedLoop:
    plant = Plant(PLANT_NUM, PLANT_DEN)
    return PIDClosedLoop(
        plant,
        Kp=1.0,
        Ti=1.0,
        Td=0.0,
        Tf=0.0,
        control_constraint=list(CONTROL_CONSTRAINT),
        anti_windup_method=ANTI_WINDUP,
    )


def build_objective(config: ConstraintConfig) -> PsoFunc:
    pid = build_pid_closed_loop()
    r, l, n = build_step_signal()

    return PsoFunc(
        pid,
        TIME_CONFIG["t0"],
        TIME_CONFIG["t1"],
        TIME_CONFIG["dt"],
        r=r,
        l=l,
        n=n,
        solver=MySolver.RK4,
        performance_index=PERFORMANCE_INDEX,
        swarm_size=PSO_CONFIG["swarm_size"],
        pre_compiling=False,
        use_freq_metrics=config.use_freq_metrics,
        tf_tuning_factor_n=TF_CONFIG["tuning_factor_n"],
        tf_limit_factor_k=TF_CONFIG["limit_factor_k"],
        sampling_rate_hz=TF_CONFIG["sampling_rate_hz"],
        freq_low_exp=FREQ_GRID["low_exp"],
        freq_high_exp=FREQ_GRID["high_exp"],
        freq_points=FREQ_GRID["points"],
        pm_min_deg=config.pm_min_deg,
        gm_min_db=config.gm_min_db,
        ms_max_db=config.ms_max_db,
        use_overshoot_control=config.use_overshoot_control,
        allowed_overshoot_pct=config.allowed_overshoot_pct,
        calculate_overshoot=True,
        use_max_du_dt_constraint=config.use_max_du_dt_constraint,
        calculate_max_du_dt=True,
        allowed_max_du_dt=config.allowed_max_du_dt,
        du_dt_window_steps=config.du_dt_window_steps,
        enable_logging=False,
    )


def build_bounds() -> list[list[float]]:
    return [
        [PID_BOUNDS["kp"][0], PID_BOUNDS["ti"][0], PID_BOUNDS["td"][0]],
        [PID_BOUNDS["kp"][1], PID_BOUNDS["ti"][1], PID_BOUNDS["td"][1]],
    ]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv_header(path: Path, fieldnames: list[str]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()


def append_csv_row(path: Path, fieldnames: list[str], row: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writerow(row)


def build_manifest_rows(
    num_runs: int,
    base_seed: int,
    configs: list[ConstraintConfig],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for config in configs:
        rows.append(
            {
                "config_id": config.config_id,
                "family": config.family,
                "hardness": config.hardness,
                "threshold_value": config.threshold_value,
                "threshold_unit": config.threshold_unit,
                "use_freq_metrics": int(config.use_freq_metrics),
                "pm_min_deg": config.pm_min_deg,
                "gm_min_db": config.gm_min_db,
                "ms_max_db": "" if config.ms_max_db is None else config.ms_max_db,
                "use_overshoot_control": int(config.use_overshoot_control),
                "allowed_overshoot_pct": config.allowed_overshoot_pct,
                "use_max_du_dt_constraint": int(config.use_max_du_dt_constraint),
                "allowed_max_du_dt": config.allowed_max_du_dt,
                "du_dt_window_steps": config.du_dt_window_steps,
                "num_runs": num_runs,
                "base_seed": base_seed,
                "swarm_size": PSO_CONFIG["swarm_size"],
                "max_iter": PSO_CONFIG["max_iter"],
            }
        )
    return rows


def make_seed(base_seed: int, config_index: int, run_id: int) -> int:
    return int(base_seed + 100000 * config_index + run_id)


def record_iteration_row(
    *,
    iteration_rows_path: Path,
    iteration_fields: list[str],
    config: ConstraintConfig,
    run_id: int,
    seed: int,
    iteration: int,
    feasible_so_far: bool,
    best_so_far_violation: float,
    best_so_far_feasible_cost: float,
    best_so_far_objective_cost: float,
) -> None:
    append_csv_row(
        iteration_rows_path,
        iteration_fields,
        {
            "config_id": config.config_id,
            "family": config.family,
            "hardness": config.hardness,
            "threshold_value": config.threshold_value,
            "threshold_unit": config.threshold_unit,
            "run_id": run_id,
            "seed": seed,
            "iteration": iteration,
            "feasible_so_far": int(feasible_so_far),
            "best_so_far_violation": best_so_far_violation,
            "best_so_far_feasible_cost": "" if math.isnan(best_so_far_feasible_cost) else best_so_far_feasible_cost,
            "best_so_far_objective_cost": best_so_far_objective_cost,
        },
    )


def run_single_configuration(
    *,
    config: ConstraintConfig,
    config_index: int,
    num_runs: int,
    base_seed: int,
    run_summary_path: Path,
    run_summary_fields: list[str],
    iteration_trace_path: Path,
    iteration_fields: list[str],
) -> None:
    objective = build_objective(config)
    bounds = build_bounds()

    for run_id in range(num_runs):
        seed = make_seed(base_seed, config_index, run_id)
        random.seed(seed)
        np.random.seed(seed)

        swarm = Swarm(
            objective,
            size=PSO_CONFIG["swarm_size"],
            param_number=3,
            bounds=bounds,
            randomness=PSO_CONFIG["randomness"],
            u1=PSO_CONFIG["u1"],
            u2=PSO_CONFIG["u2"],
            initial_range=PSO_CONFIG["initial_range"],
            initial_swarm_span=PSO_CONFIG["initial_swarm_span"],
            min_neighbors_fraction=PSO_CONFIG["min_neighbors_fraction"],
            max_stall=PSO_CONFIG["max_stall"],
            max_iter=PSO_CONFIG["max_iter"],
            stall_windows_required=PSO_CONFIG["stall_windows_required"],
            space_factor=PSO_CONFIG["space_factor"],
            convergence_factor=PSO_CONFIG["convergence_factor"],
        )

        first_feasible_iteration: int | None = 0 if swarm.gBest.p_best_feasible else None

        record_iteration_row(
            iteration_rows_path=iteration_trace_path,
            iteration_fields=iteration_fields,
            config=config,
            run_id=run_id,
            seed=seed,
            iteration=0,
            feasible_so_far=bool(swarm.gBest.p_best_feasible),
            best_so_far_violation=float(swarm.gBest.p_best_violation),
            best_so_far_feasible_cost=(
                float(swarm.gBest.p_best_perf) if swarm.gBest.p_best_feasible else math.nan
            ),
            best_so_far_objective_cost=float(swarm.gBest.p_best_cost),
        )

        def iterate_callback(current_swarm: Swarm) -> None:
            nonlocal first_feasible_iteration
            if current_swarm.gBest.p_best_feasible and first_feasible_iteration is None:
                first_feasible_iteration = int(current_swarm.iterations)

            record_iteration_row(
                iteration_rows_path=iteration_trace_path,
                iteration_fields=iteration_fields,
                config=config,
                run_id=run_id,
                seed=seed,
                iteration=int(current_swarm.iterations),
                feasible_so_far=bool(current_swarm.gBest.p_best_feasible),
                best_so_far_violation=float(current_swarm.gBest.p_best_violation),
                best_so_far_feasible_cost=(
                    float(current_swarm.gBest.p_best_perf)
                    if current_swarm.gBest.p_best_feasible
                    else math.nan
                ),
                best_so_far_objective_cost=float(current_swarm.gBest.p_best_cost),
            )

        best_position, _ = swarm.simulate_swarm(iterate_func=iterate_callback)

        best_kp = float(best_position[0])
        best_ti = float(best_position[1])
        best_td = float(best_position[2])
        tf_report = compute_effective_tf_report(
            Td=best_td,
            dt=TIME_CONFIG["dt"],
            tf_tuning_factor_n=TF_CONFIG["tuning_factor_n"],
            tf_limit_factor_k=TF_CONFIG["limit_factor_k"],
            sampling_rate_hz=TF_CONFIG["sampling_rate_hz"],
        )

        append_csv_row(
            run_summary_path,
            run_summary_fields,
            {
                "config_id": config.config_id,
                "family": config.family,
                "hardness": config.hardness,
                "threshold_value": config.threshold_value,
                "threshold_unit": config.threshold_unit,
                "run_id": run_id,
                "seed": seed,
                "feasible_found": int(swarm.gBest.p_best_feasible),
                "first_feasible_iteration": "" if first_feasible_iteration is None else first_feasible_iteration,
                "stop_iteration": int(swarm.iterations),
                "final_best_objective_cost": float(swarm.gBest.p_best_cost),
                "final_best_violation": float(swarm.gBest.p_best_violation),
                "final_best_feasible_cost": (
                    "" if not swarm.gBest.p_best_feasible else float(swarm.gBest.p_best_perf)
                ),
                "final_best_kp": best_kp,
                "final_best_ti": best_ti,
                "final_best_td": best_td,
                "final_best_tf": float(tf_report.tf_effective),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the PSO convergence study for the configured constraint cases "
            "and store run-level plus iteration-level data."
        )
    )
    parser.add_argument(
        "--num-runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"Number of PSO runs per configuration (default: {DEFAULT_RUNS}).",
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=DEFAULT_BASE_SEED,
        help=f"Base seed for reproducible run initialization (default: {DEFAULT_BASE_SEED}).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(
            Path(__file__).resolve().parent
            / "results"
            / "pt2_d01_u100_convergence_runs_with_reference"
        ),
        help="Directory for the generated CSV files.",
    )
    parser.add_argument(
        "--config-id",
        action="append",
        dest="config_ids",
        help=(
            "Optional config_id filter. Can be passed multiple times, e.g. "
            "--config-id reference_unconstrained"
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_configs = ALL_CONFIGS
    if args.config_ids:
        requested = set(args.config_ids)
        selected_configs = [config for config in ALL_CONFIGS if config.config_id in requested]
        missing = sorted(requested - {config.config_id for config in selected_configs})
        if missing:
            raise ValueError(f"Unknown config_id values: {', '.join(missing)}")

    manifest_path = output_dir / "config_manifest.csv"
    run_summary_path = output_dir / "run_summary.csv"
    iteration_trace_path = output_dir / "iteration_trace.csv"

    manifest_fields = [
        "config_id",
        "family",
        "hardness",
        "threshold_value",
        "threshold_unit",
        "use_freq_metrics",
        "pm_min_deg",
        "gm_min_db",
        "ms_max_db",
        "use_overshoot_control",
        "allowed_overshoot_pct",
        "use_max_du_dt_constraint",
        "allowed_max_du_dt",
        "du_dt_window_steps",
        "num_runs",
        "base_seed",
        "swarm_size",
        "max_iter",
    ]
    run_summary_fields = [
        "config_id",
        "family",
        "hardness",
        "threshold_value",
        "threshold_unit",
        "run_id",
        "seed",
        "feasible_found",
        "first_feasible_iteration",
        "stop_iteration",
        "final_best_objective_cost",
        "final_best_violation",
        "final_best_feasible_cost",
        "final_best_kp",
        "final_best_ti",
        "final_best_td",
        "final_best_tf",
    ]
    iteration_fields = [
        "config_id",
        "family",
        "hardness",
        "threshold_value",
        "threshold_unit",
        "run_id",
        "seed",
        "iteration",
        "feasible_so_far",
        "best_so_far_violation",
        "best_so_far_feasible_cost",
        "best_so_far_objective_cost",
    ]

    write_csv_header(manifest_path, manifest_fields)
    write_csv_header(run_summary_path, run_summary_fields)
    write_csv_header(iteration_trace_path, iteration_fields)

    for row in build_manifest_rows(
        num_runs=args.num_runs,
        base_seed=args.base_seed,
        configs=selected_configs,
    ):
        append_csv_row(manifest_path, manifest_fields, row)

    print("Starting PSO convergence study...")
    print(f"Output directory: {output_dir}")
    print(f"Configurations: {len(selected_configs)}")
    print(f"Runs per configuration: {args.num_runs}")

    for config_index, config in enumerate(selected_configs):
        print(
            f"[{config_index + 1:02d}/{len(selected_configs):02d}] "
            f"{config.config_id} | family={config.family} | hardness={config.hardness}"
        )
        run_single_configuration(
            config=config,
            config_index=config_index,
            num_runs=args.num_runs,
            base_seed=args.base_seed,
            run_summary_path=run_summary_path,
            run_summary_fields=run_summary_fields,
            iteration_trace_path=iteration_trace_path,
            iteration_fields=iteration_fields,
        )

    print("Study finished.")
    print(f"Wrote manifest to:       {manifest_path}")
    print(f"Wrote run summaries to:  {run_summary_path}")
    print(f"Wrote iteration trace to:{iteration_trace_path}")


if __name__ == "__main__":
    main()
