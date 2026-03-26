# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Script:        main.py
# Description:   Serves as the entry point of the PID Optimizer. Loads configuration settings,
#                initializes the plant and PID controller, constructs the PSO objective
#                function, runs the optimization loop with progress feedback, and generates a
#                comprehensive report with the final tuned parameters and system responses.
#
# Authors:       Florin Büchi, Thomas Stähli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zürcher Hochschule für angewandte Wissenschaften (or internal use only)
# ──────────────────────────────────────────────────────────────────────────────


import sys
from pathlib import Path

import numpy as np
from tqdm import tqdm

from app_domain.PSO import Swarm
#from services.config_loader import load_config, ConfigError
from app_domain.controlsys import (
    Plant,
    PIDClosedLoop,
    PsoFunc,
    compute_effective_tf_report,
    settling_time,
    AntiWindup,
    PerformanceIndex,
    bode_plot,
    crossover_frequency,
)
#from services.report_generator import report_generator
from app_domain.controlsys.freq_metrics import compute_loop_metrics_batch_from_frf
import matplotlib.pyplot as plt

print("Starting the PID Optimizer. Loading modules, please wait...")


def print_result_block(title: str, data: dict) -> None:
    """Print a result block with spacing between entries for CLI readability."""
    print(f"\n=== {title} ===")
    for key, value in data.items():
        print(f"{key}: {value}")


def main():

    '''print("Loading Configuration..")

    try:
        config = load_config()
        print("Configuration loaded successfully!")
    except ConfigError as e:
        print("error in configuration!:")
        print(e)
        input("Press Enter to exit..")
        return'''

    '''plant_num = config["system"]["plant"]["numerator"]
    plant_den = config["system"]["plant"]["denominator"]

    sim_mode = config["system"]["simulation_time"]["mode"]
    start_time = config["system"]["simulation_time"]["start_time"]
    end_time = config["system"]["simulation_time"]["end_time"]
    time_step = config["system"]["simulation_time"]["time_step"]

    anti_windup = config["system"]["anti_windup"]

    excitation_target = config["system"]["excitation_target"]

    constraint_min = config["system"]["control_constraint"]["min_constraint"]
    constraint_max = config["system"]["control_constraint"]["max_constraint"]

    performance_index = config["system"]["performance_index"]

    swarm_size = config["pso"]["swarm_size"]
    iterations = config["pso"]["iterations"]

    kp_min = config["pso"]["bounds"]["kp_min"]
    kp_max = config["pso"]["bounds"]["kp_max"]
    ti_min = config["pso"]["bounds"]["ti_min"]
    ti_max = config["pso"]["bounds"]["ti_max"]
    td_min = config["pso"]["bounds"]["td_min"]
    td_max = config["pso"]["bounds"]["td_max"]'''

    plant_num = [1]
    plant_den = [1, 0.1, 1]

    use_freq_metrics = True
    pm_min_deg = 70
    gm_min_db = 10
    ms_max_db = 20 * np.log10(2.0)

    use_overshoot_control = True
    allowed_overshoot_pct = 1
    # Normalized total variation of u_sat:
    # sum(|u[k] - u[k-1]|) / ((t1 - t0) * (u_max - u_min))
    # Keep disabled until the log data has been used to calibrate a limit.
    use_control_activity_constraint = False
    allowed_control_activity = 0.05

    sim_mode = "fixed"
    start_time = 0
    end_time = 20
    time_step = 1e-4

    anti_windup = AntiWindup.CLAMPING

    excitation_target = "reference"

    constraint_min = -100
    constraint_max = 100

    performance_index = PerformanceIndex.ITAE

    swarm_size = 40
    iterations = 14

    kp_min = 0
    kp_max = 10
    ti_min = 0.1
    ti_max = 10
    td_min = 0
    td_max = 10
    tf_tuning_factor_n = 5.0
    tf_limit_factor_k = 5.0
    sampling_rate_hz = None

    # generate plant
    plant: Plant = Plant(plant_num, plant_den)
    bounds = [[kp_min, ti_min, td_min], [kp_max, ti_max, td_max]]

    # generate closed loop
    pid: PIDClosedLoop = PIDClosedLoop(plant, Kp=10, Ti=5, Td=3, Tf=0.0,
                                       control_constraint=[constraint_min, constraint_max],
                                       anti_windup_method=anti_windup)

    # generate function to be optimized
    r = lambda t: np.zeros_like(t)
    l = lambda t: np.zeros_like(t)
    n = lambda t: np.zeros_like(t)

    match excitation_target:
        case "reference":
            r = lambda t: np.ones_like(t)
        case "input_disturbance":
            l = lambda t: np.ones_like(t)
        case "measurement_disturbance":
            n = lambda t: np.ones_like(t)

    # in case of sim-mode 'auto', find settling time of plant
    if sim_mode == "auto" and excitation_target == "reference":
        t_set, y_set = plant.system_response(u=r, t0=start_time, t1=end_time, dt=time_step)
        end_time = settling_time(t=t_set, y=y_set, r=r, tolerance=0.05, max_allowed_time=end_time)

    base_dir = Path(__file__).resolve().parent
    log_file = base_dir / "particle_log.csv"

    # Fresh logfile per run to avoid mixed legacy separators/headers.
    if log_file.exists():
        log_file.unlink()

    obj_func = PsoFunc(
        pid,
        start_time, end_time, time_step,
        r=r, l=l, n=n,
        use_freq_metrics=use_freq_metrics,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
        sampling_rate_hz=sampling_rate_hz,
        freq_low_exp=-2,
        freq_high_exp=5,
        freq_points=600,
        pm_min_deg=pm_min_deg,
        gm_min_db=gm_min_db,
        ms_max_db=ms_max_db,
        use_overshoot_control=use_overshoot_control,
        allowed_overshoot_pct=allowed_overshoot_pct,
        use_control_activity_constraint=use_control_activity_constraint,
        allowed_control_activity=allowed_control_activity,
        performance_index=performance_index,
        swarm_size=swarm_size,
        enable_logging=True,
        log_path=str(log_file),
    )

    # init values
    best_Kp = 0
    best_Ti = 0
    best_Td = 0
    # NOTE: this is the scalar objective/cost returned by PSO (BIG-M compatible),
    # not necessarily a pure performance index J for infeasible candidates.
    best_objective_cost = sys.float_info.max

    # progressbar
    pbar = tqdm(range(iterations), desc="Processing", unit="step", colour="green")



    for run_idx in pbar:
        obj_func.set_run_id(run_idx)
        swarm = Swarm(obj_func, swarm_size, 3, bounds)
        swarm_result, objective_cost_val = swarm.simulate_swarm()

        # Best parameters from the swarm
        Kp = swarm_result[0]
        Ti = swarm_result[1]
        Td = swarm_result[2]

        if objective_cost_val < best_objective_cost:
            best_objective_cost = objective_cost_val
            best_Kp = Kp
            best_Ti = Ti
            best_Td = Td

    # Set parameters
    pid.set_pid_param(Kp=best_Kp, Ti=best_Ti, Td=best_Td)
    tf_report = compute_effective_tf_report(
        Td=best_Td,
        dt=time_step,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
        sampling_rate_hz=sampling_rate_hz,
    )
    pid.set_filter(Tf=tf_report.tf_effective)
    best_eval = obj_func.evaluate_candidates(np.array([[best_Kp, best_Ti, best_Td]], dtype=np.float64))
    best_control_activity = float(best_eval["control_activity"][0])

    data = {
        "best_Kp": best_Kp,
        "best_Ti": best_Ti,
        "best_Td": best_Td,
        "best_Tf": tf_report.tf_effective,
        "best_control_activity": best_control_activity,
        "performance_index": performance_index,
        # Backward-compatible key name kept for existing consumers.
        "best_performance_index": best_objective_cost,
        "best_objective_cost": best_objective_cost,

        "plant": plant,
        "pid": pid,

        "anti_windup_method": anti_windup,
        "constraint_min": constraint_min,
        "constraint_max": constraint_max,

        "start_time": start_time,
        "end_time": end_time,
        "time_step": time_step,
        "sim_mode": sim_mode,
        "excitation_target": excitation_target,

        "plant_num": plant_num,
        "plant_den": plant_den,
        "use_control_activity_constraint": use_control_activity_constraint,
        "allowed_control_activity": allowed_control_activity,
    }

    print_result_block("Best PID summary", data)

    # --------------------------------------------------
    # Frequency metrics for best solution (DEBUG)
    # --------------------------------------------------
    w_dbg = np.logspace(-2, 5, 600)
    s_dbg = 1j * w_dbg
    G_dbg = plant.system(s_dbg)

    metrics_dbg = compute_loop_metrics_batch_from_frf(
        G=G_dbg,
        w=w_dbg,
        Kp=np.array([best_Kp]),
        Ti=np.array([best_Ti]),
        Td=np.array([best_Td]),
        Tf=np.array([pid.Tf]),
    )

    pm_dbg = metrics_dbg["pm_deg"][0]
    gm_dbg = metrics_dbg["gm_db"][0]
    ms_dbg = metrics_dbg["ms_db"][0]
    has_wc_dbg = metrics_dbg["has_wc"][0]
    has_w180_dbg = metrics_dbg["has_w180"][0]

    print("\n=== Frequency metrics (best PID) ===")
    print(f"PM  [deg]: {pm_dbg:.3f}   (has_wc={has_wc_dbg})")
    print(f"GM  [dB ]: {gm_dbg:.3f}   (has_w180={has_w180_dbg})")
    print(f"Ms  [dB ]: {ms_dbg:.3f}")
    print("\n=== Control activity (best PID) ===")
    print(f"control_activity: {best_control_activity:.6f}")


    # --- Open-loop step ---
    t_ol, y_ol = plant.step_response(
        t0=start_time,
        t1=end_time,
        dt=time_step,
    )

    systems_for_bode = {}

    plt.figure()

    match excitation_target:
        case "reference":
            t_cl, _, y_cl = pid.step_response(
                t0=start_time,
                t1=end_time,
                dt=time_step,
            )
            systems_for_bode["Plant"] = plant.system
            systems_for_bode["Closed Loop"] = pid.closed_loop

            plt.plot(t_ol, y_ol, label="Plant")
            plt.plot(t_cl, y_cl, label="Closed Loop")

        case "input_disturbance":
            t_cl, _, y_cl = pid.step_response_l(
                t0=start_time,
                t1=end_time,
                dt=time_step,
            )
            systems_for_bode["Closed Loop input disturbance"] = pid.closed_loop_l
            plt.plot(t_cl, y_cl, label="Closed Loop input disturbance")

        case "measurement_disturbance":
            t_cl, _, y_cl = pid.step_response_n(
                t0=start_time,
                t1=end_time,
                dt=time_step,
            )
            systems_for_bode["Closed Loop measurement disturbance"] = pid.closed_loop_n
            plt.plot(t_cl, y_cl, label="Closed Loop measurement disturbance")

    plt.xlabel("time / s")
    plt.ylabel("output")
    plt.title("Step Response")
    plt.grid(True)
    plt.legend()

    systems_for_bode["Open Loop L=C*G"] = lambda s: pid.controller(s) * plant.system(s)
    systems_for_bode["Sensitivity S=1/(1+L)"] = (
        lambda s: 1.0 / (1.0 + pid.controller(s) * plant.system(s))
    )

    # --- Bode ---
    bode_fig = bode_plot(systems_for_bode, high_exp=5)

    plt.show()  # ← für temporären Test


if __name__ == "__main__":
    main()
