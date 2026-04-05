from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app_domain.controlsys import (
    AntiWindup,
    MySolver,
    PIDClosedLoop,
    PerformanceIndex,
    Plant,
    PsoFunc,
)


# Strecke
plant_num = [1]
plant_den = [1, 2, 1]

# PID
Kp = 10
Ti = 9.5608
Td = 0.2972

# Simulation / Kosten
t0 = 0.0
t1 = 20.0
dt = 1e-4
control_constraint = (-2.0, 2.0)
anti_windup = AntiWindup.CLAMPING
ka = 1/10.0
solver = MySolver.RK4
performance_index = PerformanceIndex.ITAE
tf_tuning_factor_n = 5.0
tf_limit_factor_k = 5.0


def main() -> None:
    plant = Plant(num=plant_num, den=plant_den)
    controller = PIDClosedLoop(
        plant,
        Kp=Kp,
        Ti=Ti,
        Td=Td,
        control_constraint=list(control_constraint),
        anti_windup_method=anti_windup,
        ka=ka,
    )

    r = lambda t: np.ones_like(t)
    l = lambda t: np.zeros_like(t)
    n = lambda t: np.zeros_like(t)

    objective = PsoFunc(
        controller=controller,
        t0=t0,
        t1=t1,
        dt=dt,
        r=r,
        l=l,
        n=n,
        solver=solver,
        performance_index=performance_index,
        swarm_size=1,
        pre_compiling=False,
        use_freq_metrics=False,
        use_overshoot_control=False,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
    )

    tf_report = objective.evaluate_tf_for_td(Td)
    controller.set_filter(tf_report.tf_effective)

    result = objective.evaluate_candidates(
        np.array([[Kp, Ti, Td]], dtype=np.float64)
    )

    cost = float(result["cost"][0])
    perf = float(result["perf"][0])
    feasible = bool(result["feasible"][0])
    violation = float(result["violation"][0])

    t_eval, u_eval, y_eval = controller.system_response(
        t0=t0,
        t1=t1,
        dt=dt,
        r=r,
        l=l,
        n=n,
        solver=solver,
    )

    print("Plant:")
    print(f"  num = {plant_num}")
    print(f"  den = {plant_den}")
    print("PID:")
    print(f"  Kp = {Kp}")
    print(f"  Ti = {Ti}")
    print(f"  Td = {Td}")
    print("D-Filter:")
    print(f"  N                 = {tf_tuning_factor_n}")
    print(f"  limit factor k    = {tf_limit_factor_k}")
    print(f"  Tf_raw            = {tf_report.tf_raw}")
    print(f"  Tf_eff            = {tf_report.tf_effective}")
    print(f"  Tf_min            = {tf_report.tf_min}")
    print(f"  limited           = {tf_report.limited}")
    print("Setup:")
    print(f"  anti_windup       = {anti_windup.name}")
    print(f"  ka                = {ka}")
    print(f"  performance_index = {performance_index.name}")
    print(f"  constraint        = {control_constraint}")
    print(f"  t0, t1, dt        = {t0}, {t1}, {dt}")
    print("Result:")
    print(f"  feasible  = {feasible}")
    print(f"  violation = {violation}")
    print(f"  perf_J    = {perf}")
    print(f"  cost      = {cost}")

    fig, (ax_y, ax_u) = plt.subplots(2, 1, sharex=True, figsize=(10, 7))
    fig.suptitle(
        f"Backcalculation Verification | Tf_eff = {tf_report.tf_effective:.6f} s"
    )

    ax_y.plot(t_eval, y_eval, label="y(t)")
    ax_y.axhline(1.0, color="0.4", linestyle="--", linewidth=1.0, label="r(t)")
    ax_y.set_ylabel("y(t)")
    ax_y.grid(True)
    ax_y.legend()
    ax_y.text(
        0.02,
        0.98,
        (
            f"Tf_raw = {tf_report.tf_raw:.6f} s\n"
            f"Tf_eff = {tf_report.tf_effective:.6f} s\n"
            f"limited = {tf_report.limited}"
        ),
        transform=ax_y.transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    ax_u.plot(t_eval, u_eval, label="u(t)", color="tab:orange")
    ax_u.axhline(control_constraint[0], color="tab:red", linestyle="--", linewidth=1.0)
    ax_u.axhline(control_constraint[1], color="tab:red", linestyle="--", linewidth=1.0)
    ax_u.set_xlabel("t")
    ax_u.set_ylabel("u(t)")
    ax_u.grid(True)
    ax_u.legend()

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
