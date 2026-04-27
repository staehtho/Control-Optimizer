from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app_domain.PSO import Swarm
from app_domain.controlsys import (
    AntiWindup,
    PIDClosedLoop,
    PerformanceIndex,
    Plant,
    dominant_pole_realpart,
)
from app_domain.pso_objective import PsoFunc


def load_cases_from_excel(xlsx_path: Path) -> list[dict]:
    raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)

    ptn_row = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("PTn")][0]
    pt2_row = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("PT2")][0]

    ptn_header_row = ptn_row + 1
    ptn_df = raw.iloc[ptn_header_row + 1 : pt2_row].copy()
    ptn_df.columns = raw.iloc[ptn_header_row].tolist()
    ptn_df = ptn_df.dropna(how="all")
    ptn_df = ptn_df.rename(columns={"n": "param", "ITAE_PSO_python": "itae_reference"})
    ptn_df["A"] = ptn_df["UpperLimit"].astype(float).abs()

    pt2_header_row = pt2_row + 1
    pt2_df = raw.iloc[pt2_header_row + 1 :].copy()
    pt2_df.columns = raw.iloc[pt2_header_row].tolist()
    pt2_df = pt2_df.dropna(how="all")
    pt2_df = pt2_df.rename(columns={"D": "param", "ITAE_PSO_python": "itae_reference"})
    pt2_df["A"] = pt2_df["UpperLimit"].astype(float).abs()

    cases: list[dict] = []

    for _, row in ptn_df.iterrows():
        n_value = int(row["param"])
        denominator = (np.poly1d([1.0, 1.0]) ** n_value).c.tolist()
        cases.append(
            {
                "type": "PTn",
                "n_or_D": n_value,
                "A": float(row["A"]),
                "plant_num": [1.0],
                "plant_den": denominator,
                "ref_kp": float(row["Kp_PSO"]),
                "ref_ti": float(row["Ti_PSO"]),
                "ref_td": float(row["Td_PSO"]),
                "itae_reference": float(row["itae_reference"]),
            }
        )

    for _, row in pt2_df.iterrows():
        damping = float(row["param"])
        cases.append(
            {
                "type": "PT2",
                "n_or_D": damping,
                "A": float(row["A"]),
                "plant_num": [1.0],
                "plant_den": [1.0, 2.0 * damping, 1.0],
                "ref_kp": float(row["Kp_PSO"]),
                "ref_ti": float(row["Ti_PSO"]),
                "ref_td": float(row["Td_PSO"]),
                "itae_reference": float(row["itae_reference"]),
            }
        )

    return cases


def compute_old_tf(denominator: list[float]) -> float:
    p_dom = dominant_pole_realpart(denominator)
    if p_dom is None:
        return 0.01
    return (1.0 / abs(p_dom)) / 100.0


def run_one_case(
    case: dict,
    *,
    swarm_size: int = 40,
    iterations: int = 14,
    start_time: float = 0.0,
    end_time: float = 20.0,
    time_step: float = 1e-4,
    kp_min: float = 0.0,
    kp_max: float = 10.0,
    ti_min: float = 0.1,
    ti_max: float = 10.0,
    td_min: float = 0.0,
    td_max: float = 10.0,
    anti_windup: AntiWindup = AntiWindup.CLAMPING,
    performance_index: PerformanceIndex = PerformanceIndex.ITAE,
    tf_tuning_factor_n: float = 5.0,
    tf_limit_factor_k: float = 5.0,
    sampling_rate_hz: float | None = None,
) -> dict:
    plant = Plant(case["plant_num"], case["plant_den"])
    bounds = [[kp_min, ti_min, td_min], [kp_max, ti_max, td_max]]

    pid = PIDClosedLoop(
        plant,
        Kp=10.0,
        Ti=5.0,
        Td=3.0,
        Tf=0.0,
        control_constraint=[-case["A"], case["A"]],
        anti_windup_method=anti_windup,
    )

    objective = PsoFunc(
        pid,
        start_time,
        end_time,
        time_step,
        r=lambda t: np.ones_like(t),
        l=lambda t: np.zeros_like(t),
        n=lambda t: np.zeros_like(t),
        performance_index=performance_index,
        swarm_size=swarm_size,
        pre_compiling=False,
        use_freq_metrics=False,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
        sampling_rate_hz=sampling_rate_hz,
    )

    best = {"Kp": 0.0, "Ti": 0.0, "Td": 0.0, "itae_new": sys.float_info.max}

    for _ in range(iterations):
        swarm = Swarm(objective, swarm_size, 3, bounds)
        result, cost = swarm.simulate_swarm()
        if cost < best["itae_new"]:
            best.update(
                {
                    "Kp": float(result[0]),
                    "Ti": float(result[1]),
                    "Td": float(result[2]),
                    "itae_new": float(cost),
                }
            )

    tf_report = objective.evaluate_tf_for_td(best["Td"])
    tf_old = compute_old_tf(case["plant_den"])

    return {
        "type": case["type"],
        "n_or_D": case["n_or_D"],
        "A": case["A"],
        "plant_num": str(case["plant_num"]),
        "plant_den": str(case["plant_den"]),
        "ref_kp": case["ref_kp"],
        "ref_ti": case["ref_ti"],
        "ref_td": case["ref_td"],
        "itae_reference": case["itae_reference"],
        "best_kp_new": best["Kp"],
        "best_ti_new": best["Ti"],
        "best_td_new": best["Td"],
        "itae_new": best["itae_new"],
        "itae_delta": best["itae_new"] - case["itae_reference"],
        "tf_new_raw": tf_report.tf_raw,
        "tf_new_effective": tf_report.tf_effective,
        "tf_old_fixed": tf_old,
        "tf_limited": tf_report.limited,
        "tf_limited_by_simulation": tf_report.limited_by_simulation,
        "tf_limited_by_sampling": tf_report.limited_by_sampling,
        "tf_min_sampling_rate_hz": tf_report.min_sampling_rate_hz,
        "tf_tuning_factor_n": tf_tuning_factor_n,
        "tf_limit_factor_k": tf_limit_factor_k,
        "sampling_rate_hz": sampling_rate_hz,
        "time_step": time_step,
        "swarm_size": swarm_size,
        "iterations": iterations,
    }


def run_batch(
    xlsx_path: Path,
    out_path: Path,
    *,
    swarm_size: int = 40,
    iterations: int = 14,
    start_time: float = 0.0,
    end_time: float = 20.0,
    time_step: float = 1e-4,
    tf_tuning_factor_n: float = 5.0,
    tf_limit_factor_k: float = 5.0,
    sampling_rate_hz: float | None = None,
) -> pd.DataFrame:
    cases = load_cases_from_excel(xlsx_path)

    results: list[dict] = []
    for case in tqdm(cases, desc="Tf generation batch", unit="case", colour="green"):
        results.append(
            run_one_case(
                case,
                swarm_size=swarm_size,
                iterations=iterations,
                start_time=start_time,
                end_time=end_time,
                time_step=time_step,
                tf_tuning_factor_n=tf_tuning_factor_n,
                tf_limit_factor_k=tf_limit_factor_k,
                sampling_rate_hz=sampling_rate_hz,
            )
        )

    df = pd.DataFrame(results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False)
    print(f"\nFertig. Ergebnis gespeichert in: {out_path}")
    return df


def main() -> None:
    folder = Path(__file__).resolve().parent
    excel_path = folder / "Referenzsysteme.xlsx"
    out_path = folder / "batch_results_tf_generation.xlsx"

    run_batch(
        excel_path,
        out_path,
        swarm_size=40,
        iterations=14,
        start_time=0.0,
        end_time=20.0,
        time_step=1e-4,
        tf_tuning_factor_n=5.0,
        tf_limit_factor_k=5.0,
        sampling_rate_hz=None,
    )


if __name__ == "__main__":
    main()
