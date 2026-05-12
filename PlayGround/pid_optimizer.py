import sys

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from app_domain.PSO import Swarm
from app_domain.controlsys.FFPIDClosedLoop import FFPIDClosedLoop
from app_domain.controlsys.PIClosedLoop import PIClosedLoop
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.controlsys import (
    AntiWindup,
    ControllerType,
    PerformanceIndex,
    Plant,
    bode_plot,
    settling_time,
)
from app_domain.pso_objective import PsoFunc, compute_effective_tf_report
from app_domain.pso_objective.freq_metrics import compute_loop_metrics_batch

print("Starting the PID Optimizer. Loading modules, please wait...")


def print_result_block(title: str, data: dict) -> None:
    print(f"\n=== {title} ===")
    for key, value in data.items():
        print(f"{key}: {value}")


def build_bounds(param_names: list[str], bounds_by_name: dict[str, tuple[float, float]]) -> list[list[float]]:
    lower: list[float] = []
    upper: list[float] = []

    for name in param_names:
        if name not in bounds_by_name:
            raise KeyError(f"Missing bounds for controller parameter '{name}'.")
        param_min, param_max = bounds_by_name[name]
        lower.append(float(param_min))
        upper.append(float(param_max))

    return [lower, upper]


def build_controller(
        controller_cfg: dict,
        plant: Plant,
        param_values: np.ndarray,
        *,
        tf_value: float | None,
        control_constraint: list[float],
        anti_windup_method: AntiWindup,
        ka: float,
):
    kwargs = {
        name: float(value)
        for name, value in zip(controller_cfg["param_names"], param_values, strict=True)
    }
    if controller_cfg["tf_link_index"] >= 0:
        kwargs["Tf"] = 0.0 if tf_value is None else float(tf_value)

    return controller_cfg["controller_class"](
        plant,
        **kwargs,
        control_constraint=control_constraint,
        anti_windup_method=anti_windup_method,
        ka=ka,
    )


def build_frf_candidate_row(
        controller_cfg: dict,
        param_values: np.ndarray,
        tf_value: float | None,
) -> np.ndarray:
    row = np.asarray(param_values, dtype=np.float64)
    if controller_cfg["tf_link_index"] >= 0:
        if tf_value is None:
            raise ValueError("Controllers with derivative filter require a Tf value.")
        row = np.concatenate([row, np.array([tf_value], dtype=np.float64)])
    return row[None, :]


def main():
    plant_num = [1]
    plant_den = [1, 3, 3, 1]

    use_freq_metrics = False
    pm_min_deg = 1
    gm_min_db = 1
    ms_max_db = 3

    use_overshoot_control = True
    allowed_overshoot_pct = 0
    calculate_overshoot = True

    use_max_du_dt_constraint = False
    calculate_max_du_dt = False
    allowed_max_du_dt = 10
    du_dt_window_steps = 10

    sim_mode = "fixed"
    start_time = 0
    time_step = 1e-4
    end_time = 10

    anti_windup = AntiWindup.CLAMPING
    ka = 1

    excitation_target = "reference"

    constraint_min = -5
    constraint_max = 5

    performance_index = PerformanceIndex.ITAE

    swarm_size = 40
    iterations = 14

    tf_tuning_factor_n = 5.0
    tf_limit_factor_k = 5.0
    sampling_rate_hz = None

    # Switch controller here.
    controller_type = ControllerType.PID

    controller_initial_params = {
        ControllerType.PI: {"Kp": 10.0, "Ti": 5.0},
        ControllerType.PID: {"Kp": 10.0, "Ti": 5.0, "Td": 3.0},
        ControllerType.FFPID: {"Kp": 10.0, "Ti": 5.0, "Td": 3.0, "Kff": 0.0},
    }

    controller_param_bounds = {
        "Kp": (0.0, 10.0),
        "Ti": (0.01, 10.0),
        "Td": (0.0, 10.0),
        "Kff": (-100.0, 100.0),
    }

    controller_configs = {
        ControllerType.PI: {
            "controller_class": PIClosedLoop,
            "param_names": ["Kp", "Ti"],
            "tf_link_index": -1,
        },
        ControllerType.PID: {
            "controller_class": PIDClosedLoop,
            "param_names": ["Kp", "Ti", "Td"],
            "tf_link_index": PIDClosedLoop.tf_link_index,
        },
        ControllerType.FFPID: {
            "controller_class": FFPIDClosedLoop,
            "param_names": ["Kp", "Ti", "Td", "Kff"],
            "tf_link_index": FFPIDClosedLoop.tf_link_index,
        },
    }

    controller_cfg = controller_configs[controller_type]
    param_names = controller_cfg["param_names"]
    initial_param_dict = controller_initial_params[controller_type]
    initial_param_values = np.array([initial_param_dict[name] for name in param_names], dtype=np.float64)
    bounds = build_bounds(param_names, controller_param_bounds)

    plant = Plant(plant_num, plant_den)
    control_constraint = [constraint_min, constraint_max]
    controller = build_controller(
        controller_cfg,
        plant,
        initial_param_values,
        tf_value=0.0,
        control_constraint=control_constraint,
        anti_windup_method=anti_windup,
        ka=ka,
    )

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

    if sim_mode == "auto" and excitation_target == "reference":
        t_set, y_set = plant.system_response(u=r, t0=start_time, t1=end_time, dt=time_step)
        end_time = settling_time(t=t_set, y=y_set, r=r, tolerance=0.05, max_allowed_time=end_time)

    obj_func = PsoFunc(
        controller,
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
        calculate_overshoot=calculate_overshoot,
        use_max_du_dt_constraint=use_max_du_dt_constraint,
        calculate_max_du_dt=calculate_max_du_dt,
        allowed_max_du_dt=allowed_max_du_dt,
        du_dt_window_steps=du_dt_window_steps,
        performance_index=performance_index,
        swarm_size=swarm_size,
    )

    best_param_values = initial_param_values.copy()
    best_objective_cost = sys.float_info.max
    pso_iterations_per_run: list[int] = []
    best_run_iterations = 0

    pbar = tqdm(range(iterations), desc="Processing", unit="step", colour="green")

    for _ in pbar:
        swarm = Swarm(obj_func, swarm_size, len(param_names), bounds)
        swarm_result, objective_cost_val = swarm.simulate_swarm()
        run_iterations = int(swarm.iterations)
        pso_iterations_per_run.append(run_iterations)
        candidate = np.asarray(swarm_result[:len(param_names)], dtype=np.float64)

        if objective_cost_val < best_objective_cost:
            best_objective_cost = objective_cost_val
            best_param_values = candidate.copy()
            best_run_iterations = run_iterations

    if pso_iterations_per_run:
        vg_pso_iterations = float(np.mean(pso_iterations_per_run))
        min_pso_iterations = int(min(pso_iterations_per_run))
        max_pso_iterations = int(max(pso_iterations_per_run))
    else:
        vg_pso_iterations = 0.0
        min_pso_iterations = 0
        max_pso_iterations = 0

    tf_report = None
    tf_effective = None
    if controller_cfg["tf_link_index"] >= 0:
        td_value = float(best_param_values[controller_cfg["tf_link_index"]])
        tf_report = compute_effective_tf_report(
            Td=td_value,
            dt=time_step,
            tf_tuning_factor_n=tf_tuning_factor_n,
            tf_limit_factor_k=tf_limit_factor_k,
            sampling_rate_hz=sampling_rate_hz,
        )
        tf_effective = tf_report.tf_effective

    best_controller = build_controller(
        controller_cfg,
        plant,
        best_param_values,
        tf_value=tf_effective,
        control_constraint=control_constraint,
        anti_windup_method=anti_windup,
        ka=ka,
    )

    best_eval = obj_func.evaluate_candidates(best_param_values[None, :])
    best_overshoot_pct = float(best_eval.overshoot_pct[0])
    best_max_du_dt = float(best_eval.max_du_dt[0])

    data = {
        "controller_type": controller_type.name,
        **{
            f"best_{name}": float(value)
            for name, value in zip(param_names, best_param_values, strict=True)
        },
        "best_overshoot_pct": best_overshoot_pct,
        "best_max_du_dt": best_max_du_dt,
        "performance_index": performance_index,
        "best_performance_index": best_objective_cost,
        "best_objective_cost": best_objective_cost,
        "plant": plant,
        "controller": best_controller,
        "anti_windup_method": anti_windup,
        "ka": ka,
        "constraint_min": constraint_min,
        "constraint_max": constraint_max,
        "start_time": start_time,
        "end_time": end_time,
        "time_step": time_step,
        "sim_mode": sim_mode,
        "excitation_target": excitation_target,
        "plant_num": plant_num,
        "plant_den": plant_den,
        "calculate_overshoot": calculate_overshoot,
        "use_max_du_dt_constraint": use_max_du_dt_constraint,
        "calculate_max_du_dt": calculate_max_du_dt,
        "allowed_max_du_dt": allowed_max_du_dt,
        "du_dt_window_steps": du_dt_window_steps,
        "vg_pso_iterations": vg_pso_iterations,
        "min_pso_iterations": min_pso_iterations,
        "max_pso_iterations": max_pso_iterations,
        "best_run_iterations": best_run_iterations,
    }
    if tf_effective is not None:
        data["best_Tf"] = tf_effective

    print_result_block(f"Best {controller_type.name} summary", data)

    if tf_report is not None:
        active_limits: list[str] = []
        if tf_report.limited_by_simulation:
            active_limits.append("simulation_dt")
        if tf_report.limited_by_sampling:
            active_limits.append("sampling_rate")

        print(f"\n=== Tf evaluation (best {controller_type.name}) ===")
        print(f"N: {tf_tuning_factor_n:.3f}")
        print(f"k: {tf_limit_factor_k:.3f}")
        print(f"Td: {float(best_param_values[controller_cfg['tf_link_index']]):.6f}")
        print(f"Tf_raw = Td / N: {tf_report.tf_raw:.6f}")
        print(f"Tf_eff: {tf_report.tf_effective:.6f}")
        print(f"Tf_min: {tf_report.tf_min:.6f}")
        print(f"Simulation limit k*dt: {tf_report.simulation_limit:.6f}")
        if sampling_rate_hz is None:
            print("Sampling limit: not set")
        else:
            print(f"Sampling limit k/fs: {tf_report.sampling_limit:.6f} (fs={sampling_rate_hz:.6f} Hz)")
        print(f"Tf limited: {'yes' if tf_report.limited else 'no'}")
        print(f"Active limit(s): {', '.join(active_limits) if active_limits else 'none'}")
        print(f"Minimum sampling rate for k-spacing: {tf_report.min_sampling_rate_hz:.6f} Hz")

    print(f"\n=== Overshoot (best {controller_type.name}) ===")
    print(f"overshoot_pct: {best_overshoot_pct:.6f}")
    print(f"\n=== Max du/dt (best {controller_type.name}) ===")
    print(f"max_du_dt: {best_max_du_dt:.6f}")

    w_dbg = np.logspace(-2, 5, 600)
    X = build_frf_candidate_row(controller_cfg, best_param_values, tf_effective)
    metrics_dbg = compute_loop_metrics_batch(
        plant.system,
        controller_cfg["controller_class"].frf_batch,
        X,
        w_dbg,
    )

    pm_dbg = metrics_dbg["pm_deg"][0]
    gm_dbg = metrics_dbg["gm_db"][0]
    ms_dbg = metrics_dbg["ms_db"][0]
    has_wc_dbg = metrics_dbg["has_wc"][0]
    has_w180_dbg = metrics_dbg["has_w180"][0]

    print(f"\n=== Frequency metrics (best {controller_type.name}) ===")
    print(f"PM  [deg]: {pm_dbg:.3f}   (has_wc={has_wc_dbg})")
    print(f"GM  [dB ]: {gm_dbg:.3f}   (has_w180={has_w180_dbg})")
    print(f"Ms  [dB ]: {ms_dbg:.3f}")

    t_ol, y_ol = plant.step_response(
        t0=start_time,
        t1=end_time,
        dt=time_step,
    )

    systems_for_bode = {}
    fig, (ax_y, ax_u) = plt.subplots(2, 1, sharex=True)

    match excitation_target:
        case "reference":
            t_cl, u_cl, y_cl = best_controller.step_response(
                t0=start_time,
                t1=end_time,
                dt=time_step,
            )
            systems_for_bode["Plant"] = plant.system
            systems_for_bode["Closed Loop"] = best_controller.closed_loop

            ax_y.plot(t_ol, y_ol, label="Plant")
            ax_y.plot(t_cl, y_cl, label="Closed Loop")
            ax_u.plot(t_cl, u_cl, label="u_sat")

        case "input_disturbance":
            t_cl, u_cl, y_cl = best_controller.step_response_l(
                t0=start_time,
                t1=end_time,
                dt=time_step,
            )
            systems_for_bode["Closed Loop input disturbance"] = best_controller.closed_loop_l
            ax_y.plot(t_cl, y_cl, label="Closed Loop input disturbance")
            ax_u.plot(t_cl, u_cl, label="u_sat")

        case "measurement_disturbance":
            t_cl, u_cl, y_cl = best_controller.step_response_n(
                t0=start_time,
                t1=end_time,
                dt=time_step,
            )
            systems_for_bode["Closed Loop measurement disturbance"] = best_controller.closed_loop_n
            ax_y.plot(t_cl, y_cl, label="Closed Loop measurement disturbance")
            ax_u.plot(t_cl, u_cl, label="u_sat")

    ax_y.set_ylabel("output")
    ax_y.set_title("Step Response")
    ax_y.grid(True)
    ax_y.legend()

    ax_u.set_xlabel("time / s")
    ax_u.set_ylabel("u_sat")
    ax_u.set_title("Control Signal")
    ax_u.grid(True)
    ax_u.legend()

    fig.tight_layout()

    systems_for_bode["Open Loop L=C*G"] = (
        lambda s: best_controller.controller(s) * plant.system(s)
    )
    systems_for_bode["Sensitivity S=1/(1+L)"] = (
        lambda s: 1.0 / (1.0 + best_controller.controller(s) * plant.system(s))
    )

    bode_plot(systems_for_bode, high_exp=5)
    plt.show()


if __name__ == "__main__":
    main()
