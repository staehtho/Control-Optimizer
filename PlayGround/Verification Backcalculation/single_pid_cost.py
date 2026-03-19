from __future__ import annotations

import sys
from pathlib import Path

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
Tf = 0.01

# Simulation / Kosten
t0 = 0.0
t1 = 20.0
dt = 1e-4
control_constraint = (-2.0, 2.0)
anti_windup = AntiWindup.CLAMPING
solver = MySolver.RK4
performance_index = PerformanceIndex.ITAE


def main() -> None:
    plant = Plant(num=plant_num, den=plant_den)
    controller = PIDClosedLoop(
        plant,
        Kp=Kp,
        Ti=Ti,
        Td=Td,
        Tf=Tf,
        control_constraint=list(control_constraint),
        anti_windup_method=anti_windup,
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
    )

    result = objective.evaluate_candidates(
        np.array([[Kp, Ti, Td]], dtype=np.float64)
    )

    cost = float(result["cost"][0])
    perf = float(result["perf"][0])
    feasible = bool(result["feasible"][0])
    violation = float(result["violation"][0])

    print("Plant:")
    print(f"  num = {plant_num}")
    print(f"  den = {plant_den}")
    print("PID:")
    print(f"  Kp = {Kp}")
    print(f"  Ti = {Ti}")
    print(f"  Td = {Td}")
    print(f"  Tf = {Tf}")
    print("Setup:")
    print(f"  anti_windup       = {anti_windup.name}")
    print(f"  performance_index = {performance_index.name}")
    print(f"  constraint        = {control_constraint}")
    print(f"  t0, t1, dt        = {t0}, {t1}, {dt}")
    print("Result:")
    print(f"  feasible  = {feasible}")
    print(f"  violation = {violation}")
    print(f"  perf_J    = {perf}")
    print(f"  cost      = {cost}")


if __name__ == "__main__":
    main()
