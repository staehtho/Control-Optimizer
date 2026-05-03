# Playground/test_freq_metrics.py
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from sympy.physics.control import PIDController

# ──────────────────────────────────────────────────────────────────────────────
# Add src to Python path so imports from src/... work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from app_domain.controlsys import Plant, bode_plot
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.pso_objective import compute_effective_tf_report
from app_domain.pso_objective.freq_metrics import compute_loop_metrics_batch


def main():
    print("=== Frequency Metrics Test (SSOT) + Bode (adaptive grid) ===")

    # -------------------------------------------------------------------------
    # Plant (edit as needed)
    # Example from your previous test:
    plant = Plant(num=[1], den=[1, 0, 1])

    # -------------------------------------------------------------------------
    # Single PID candidate (edit as needed)
    Kp = 9.973
    Ti = 4.545
    Td = 0.483
    dt = 1e-4
    tf_tuning_factor_n = 5.0
    tf_limit_factor_k = 5.0
    sampling_rate_hz = None
    tf_report = compute_effective_tf_report(
        Td=Td,
        dt=dt,
        tf_tuning_factor_n=tf_tuning_factor_n,
        tf_limit_factor_k=tf_limit_factor_k,
        sampling_rate_hz=sampling_rate_hz,
    )
    Tf = tf_report.tf_effective

    # -------------------------------------------------------------------------
    X = np.array([[Kp,
                   Ti,
                   Td,
                   Tf]])
    metrics = compute_loop_metrics_batch(
        plant.system,
        PIDClosedLoop.frf_batch,
        X=X,
        w=(-5, 5, 500)
        # Optional: override grid params if you want
        # N1=300, wmin1=1e-3, wmax1=1e3,
        # N2=450, wmin2=1e-5, wmax2=1e5,
        # phase_near_deg=15.0,
    )

    w = metrics["w"]
    pm = float(metrics["pm_deg"][0])
    gm = float(metrics["gm_db"][0])
    ms_db = float(metrics["ms_db"][0])
    has_wc = bool(metrics["has_wc"][0])
    has_w180 = bool(metrics["has_w180"][0])
    wc = float(metrics["wc"][0])
    w180 = float(metrics["w180"][0])
    ok = bool(metrics.get("ok_particles", np.array([True]))[0])

    print("\n--- Metrics (single candidate via SSOT) ---")
    print(f"Grid: w in [{w[0]:.3g}, {w[-1]:.3g}] rad/s with N={len(w)}")
    print(f"ok_particles: {ok}")
    print(f"PM  [deg]: {pm:.3f}   (has_wc={has_wc}, wc={wc:.6g} rad/s)")
    print(f"GM  [dB ]: {gm:.3f}   (has_w180={has_w180}, w180={w180:.6g} rad/s)")
    print(f"Ms  [dB ]: {ms_db:.3f}")
    print(f"Tf_raw / Tf_eff: {tf_report.tf_raw:.6f} / {tf_report.tf_effective:.6f}")

    # -------------------------------------------------------------------------
    # Bode plot (diagnostic) on the *same grid*
    pid = PIDClosedLoop(plant, Kp=Kp, Ti=Ti, Td=Td)
    pid.set_filter(Tf=Tf)

    systems_for_bode = {
        "Open Loop L=C*G": (lambda s: pid.controller(s) * plant.system(s)),
        "Sensitivity S=1/(1+L)": (lambda s: 1.0 / (1.0 + pid.controller(s) * plant.system(s))),
    }

    # Suppress divide/invalid warnings only for plotting (optional but nicer for jw-pole edge cases)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        bode_plot(systems_for_bode, omega=w, title="Bode (SSOT metrics grid)")

    plt.show()


if __name__ == "__main__":
    main()
