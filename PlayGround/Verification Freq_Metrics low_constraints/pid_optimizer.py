# ------------------------------------------------------------------------------
# Project:       PID Optimizer
# Script:        main.py
# Description:   Serves as the entry point of the PID Optimizer. Loads configuration settings,
#                initializes the plant and PID controller, constructs the PSO objective
#                function, runs the optimization loop with progress feedback, and generates a
#                comprehensive report with the final tuned parameters and system responses.
#
# Authors:       Florin Buechi, Thomas Staehli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zuercher Hochschule fuer angewandte Wissenschaften (or internal use only)
# ------------------------------------------------------------------------------

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm

from app_domain.PSO import Swarm
from app_domain.controlsys import (
    AntiWindup,
    PIDClosedLoop,
    PerformanceIndex,
    Plant,
    PsoFunc,
    bode_plot,
    compute_effective_tf_report,
    crossover_frequency,
    settling_time,
)
from app_domain.controlsys.freq_metrics import compute_loop_metrics_batch_from_frf

print("Starting the PID Optimizer. Loading modules, please wait...")


def load_cases_from_excel(xlsx_path: str):
    import numpy as np
    import pandas as pd

    raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)

    ptn_row = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("PTn")][0]
    pt2_row = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("PT2")][0]

    # --- PTn ---
    ptn_header_row = ptn_row + 1
    ptn_df = raw.iloc[ptn_header_row + 1 : pt2_row].copy()
    ptn_df.columns = raw.iloc[ptn_header_row].tolist()
    ptn_df = ptn_df.dropna(how="all")
    ptn_df = ptn_df.rename(columns={"n": "param"})
    ptn_df["A"] = ptn_df["UpperLimit"].astype(float).abs()

    # --- PT2 ---
    pt2_header_row = pt2_row + 1
    pt2_df = raw.iloc[pt2_header_row + 1 :].copy()
    pt2_df.columns = raw.iloc[pt2_header_row].tolist()
    pt2_df = pt2_df.dropna(how="all")
    pt2_df = pt2_df.rename(columns={"D": "param"})
    pt2_df["A"] = pt2_df["UpperLimit"].astype(float).abs()

    allowed = {2, 3, 5, 10}
    ptn_df = ptn_df[ptn_df["A"].isin(allowed)]
    pt2_df = pt2_df[pt2_df["A"].isin(allowed)]

    cases = []

    # --- PTn ---
    for _, r in ptn_df.iterrows():
        n = int(r["param"])
        A = float(r["A"])
        p = np.poly1d([1, 1]) ** n
        cases.append(
            {
                "type": "PTn",
                "n_or_D": n,
                "A": A,
                "plant_num": [1.0],
                "plant_den": p.c.tolist(),
            }
        )

    # --- PT2 ---
    for _, r in pt2_df.iterrows():
        D = float(r["param"])
        A = float(r["A"])
        cases.append(
            {
                "type": "PT2",
                "n_or_D": D,
                "A": A,
                "plant_num": [1.0],
                "plant_den": [1.0, 2.0 * D, 1.0],
            }
        )

    return cases


def run_one_case(
    case,
    *,
    swarm_size=40,
    iterations=14,
    sim_mode="fixed",
    start_time=0.0,
    end_time=20.0,
    time_step=1e-4,
    kp_min=0,
    kp_max=10,
    ti_min=0.1,
    ti_max=10,
    td_min=0,
    td_max=10,
    pm_min_deg=0,
    gm_min_db=0,
    ms_max_db=20,
    anti_windup=AntiWindup.CLAMPING,
    excitation_target="reference",
    performance_index=PerformanceIndex.ITAE,
    tf_tuning_factor_n=5.0,
    tf_limit_factor_k=5.0,
    sampling_rate_hz=None,
):

    plant = Plant(case["plant_num"], case["plant_den"])
    A = case["A"]
    bounds = [[kp_min, ti_min, td_min], [kp_max, ti_max, td_max]]

    pid = PIDClosedLoop(
        plant,
        Kp=10,
        Ti=5,
        Td=3,
        Tf=0.0,
        control_constraint=[-A, +A],
        anti_windup_method=anti_windup,
    )

    # Anregung (bei dir ist es ein Step auf r)
    r = lambda t: np.ones_like(t)
    l = lambda t: np.zeros_like(t)
    n = lambda t: np.zeros_like(t)

    obj_func = PsoFunc(
        pid,
        start_time,
        end_time,
        time_step,
        r=r,
        l=l,
        n=n,
        use_freq_metrics=True,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
        sampling_rate_hz=sampling_rate_hz,
        freq_low_exp=-5,
        freq_high_exp=5,
        freq_points=450,
        pm_min_deg=pm_min_deg,
        gm_min_db=gm_min_db,
        ms_max_db=ms_max_db,
        performance_index=performance_index,
        swarm_size=swarm_size,
    )

    best = {"Kp": 0.0, "Ti": 0.0, "Td": 0.0, "cost": sys.float_info.max}

    for _ in range(iterations):
        swarm = Swarm(obj_func, swarm_size, 3, bounds)
        swarm_result, best_cost = swarm.simulate_swarm()
        if best_cost < best["cost"]:
            best.update(
                {
                    "Kp": float(swarm_result[0]),
                    "Ti": float(swarm_result[1]),
                    "Td": float(swarm_result[2]),
                    "cost": float(best_cost),
                }
            )

    # Best setzen + Frequenzmetriken berechnen
    pid.set_pid_param(Kp=best["Kp"], Ti=best["Ti"], Td=best["Td"])
    tf_report = compute_effective_tf_report(
        Td=best["Td"],
        dt=time_step,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
        sampling_rate_hz=sampling_rate_hz,
    )
    pid.set_filter(Tf=tf_report.tf_effective)

    w = np.logspace(-5, 5, 600)
    s = 1j * w
    G = plant.system(s)

    metrics = compute_loop_metrics_batch_from_frf(
        G=G,
        w=w,
        Kp=np.array([best["Kp"]]),
        Ti=np.array([best["Ti"]]),
        Td=np.array([best["Td"]]),
        Tf=np.array([pid.Tf]),
    )

    out = {
        "type": case["type"],
        "n_or_D": case["n_or_D"],
        "A": A,
        "Kp": best["Kp"],
        "Ti": best["Ti"],
        "Td": best["Td"],
        "cost": best["cost"],
        "pm_deg": float(metrics["pm_deg"][0]),
        "gm_db": float(metrics["gm_db"][0]),
        "ms_db": float(metrics["ms_db"][0]),
        "has_wc": bool(metrics["has_wc"][0]),
        "has_w180": bool(metrics["has_w180"][0]),
    }
    return out


def run_batch(xlsx_path: str, out_path: str = "batch_results.xlsx"):
    cases = load_cases_from_excel(xlsx_path)

    results = []
    for case in tqdm(cases, desc="Batch", unit="case", colour="green"):
        res = run_one_case(case)
        results.append(res)

    df = pd.DataFrame(results)
    df.to_excel(out_path, index=False)

    print(f"\nFertig. Ergebnis gespeichert in: {out_path}")
    return df


def main():
    excel_path = "Referenzsysteme.xlsx"
    run_batch(excel_path)


if __name__ == "__main__":
    main()
