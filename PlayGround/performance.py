import numpy as np
from tqdm import tqdm

from app_domain.controlsys import Plant
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.pso_objective import PsoFunc
from app_domain.PSO import Swarm


def main():

    plant = Plant([1], [1, 2, 1])
    pid = PIDClosedLoop(plant)

    objective = PsoFunc(
        controller=pid,
        t0=0,
        t1=10,
        dt=1e-4,
        r=lambda t: np.ones_like(t),
        sampling_rate_hz=2e4,
        use_overshoot_control=True,
        allowed_overshoot_pct=100,
        use_max_du_dt_constraint=True,
        allowed_max_du_dt=2000,
        du_dt_window_steps=10,
        use_freq_metrics=True,
        gm_min_db=5,
        pm_min_deg=30,
        ms_max_db=10,
        pre_compiling=False,
    )

    swarm = Swarm(objective, 40, 3,[[0, 0.001, 0], [10, 10, 10]])

    print(swarm.simulate_swarm())

    for i in tqdm(range(20)):
        swarm = Swarm(objective, 40, 3,[[0, 0.001, 0], [10, 10, 10]])

        print(swarm.simulate_swarm())


if __name__ == "__main__":
    main()