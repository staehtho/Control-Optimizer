from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app_domain.controlsys import Plant
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.pso_objective.freq_metrics import compute_loop_metrics_batch


# Strecke hier eingeben
plant_num = [1]
plant_den = [1, 0.1, 1]

# PID hier eingeben
Kp = 0.5707710264568762
Ti = 0.38214362160252474
Td = 3.705771368769423

# Optional: auf einen festen Wert setzen, z.B. 0.01
# Wenn None, wird Tf automatisch aus der Strecke abgeleitet.
Tf = None

# Frequenzraster
w_min_exp = -5
w_max_exp = 5
w_points = 600


def default_tf(den: list[float]) -> float:
    roots = np.roots(np.asarray(den, dtype=float))
    stable_roots = roots[roots.real < 0.0]
    if stable_roots.size == 0:
        return 0.01
    dominant_real = np.max(stable_roots.real)
    return (1.0 / abs(dominant_real)) / 100.0


def main() -> None:
    plant = Plant(num=plant_num, den=plant_den)
    tf_used = default_tf(plant_den) if Tf is None else float(Tf)

    w = np.logspace(w_min_exp, w_max_exp, w_points)

    X = np.column_stack([Kp, Ti, Td, tf_used])
    metrics = compute_loop_metrics_batch(plant.system, PIDClosedLoop.frf_batch, X, w)

    print("Plant:")
    print(f"  num = {plant_num}")
    print(f"  den = {plant_den}")
    print("PID:")
    print(f"  Kp = {Kp}")
    print(f"  Ti = {Ti}")
    print(f"  Td = {Td}")
    print(f"  Tf = {tf_used}")
    print("Metrics:")
    print(f"  numerically_valid = {bool(metrics['numerically_valid_particles'][0])}")
    print(f"  pm_deg            = {float(metrics['pm_deg'][0])}")
    print(f"  gm_db             = {float(metrics['gm_db'][0])}")
    print(f"  ms_db             = {float(metrics['ms_db'][0])}")
    print(f"  has_wc            = {bool(metrics['has_wc'][0])}")
    print(f"  has_w180          = {bool(metrics['has_w180'][0])}")
    print(f"  wc                = {float(metrics['wc'][0])}")
    print(f"  w180              = {float(metrics['w180'][0])}")


if __name__ == "__main__":
    main()
