# Playground/test_freq_metrics.py
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# ──────────────────────────────────────────────────────────────────────────────
# 🔧 src zum Python-Path hinzufügen (damit Imports aus src/... funktionieren)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from services.controlsys import Plant, PIDClosedLoop, bode_plot

# ──────────────────────────────────────────────────────────────────────────────
def pid_controller_freq_response(Kp, Ti, Td, Tf, s):
    """C(s)=Kp*(1 + 1/(Ti*s) + (Td*s)/(Tf*s + 1))"""
    return Kp * (1.0 + 1.0 / (Ti * s) + (Td * s) / (Tf * s + 1.0))


def _interp_x_at_y(x0, y0, x1, y1, y_target):
    """Linear interpolation: find x where y crosses y_target between (x0,y0)-(x1,y1)."""
    if y1 == y0:
        return 0.5 * (x0 + x1)
    return x0 + (y_target - y0) * (x1 - x0) / (y1 - y0)


def compute_loop_metrics_single(plant, Kp, Ti, Td, Tf, w):
    """
    Compute PM [deg], GM [dB], Ms [linear] for one PID candidate.

    Policies:
      - PM missing (no 0 dB crossover): has_wc=False, pm_deg=np.nan  (=> infeasible)
      - GM missing (no -180° crossing): gm_db=+inf (=> ok for GM_min)
    """
    w = np.asarray(w, dtype=float)
    s = 1j * w

    G = plant.system(s)
    C = pid_controller_freq_response(Kp, Ti, Td, Tf, s)

    L = C * G
    S = 1.0 / (1.0 + L)

    ms = float(np.max(np.abs(S)))
    ms_db = 20.0 * np.log10(ms)

    mag_db = 20.0 * np.log10(np.maximum(np.abs(L), 1e-300))
    phase = np.unwrap(np.angle(L))  # rad

    # ── PM: 0 dB crossover ────────────────────────────────────────────────────
    target_mag_db = 0.0
    sign = np.sign(mag_db - target_mag_db)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]

    has_wc = False
    wc = np.nan
    pm_deg = np.nan

    if idx.size > 0:
        k = idx[0]  # first crossover
        wc = _interp_x_at_y(w[k], mag_db[k], w[k + 1], mag_db[k + 1], target_mag_db)

        ph0, ph1 = phase[k], phase[k + 1]
        if w[k + 1] != w[k]:
            ph_wc = ph0 + (wc - w[k]) * (ph1 - ph0) / (w[k + 1] - w[k])
        else:
            ph_wc = 0.5 * (ph0 + ph1)

        pm_deg = 180.0 + np.degrees(ph_wc)
        has_wc = True

    # ── GM: -180° crossing ────────────────────────────────────────────────────
    target_phase = -np.pi
    signp = np.sign(phase - target_phase)
    idxp = np.where(signp[:-1] * signp[1:] < 0)[0]

    has_w180 = False
    w180 = np.nan
    gm_db = np.inf

    if idxp.size > 0:
        k = idxp[0]
        w180 = _interp_x_at_y(w[k], phase[k], w[k + 1], phase[k + 1], target_phase)

        m0, m1 = np.abs(L[k]), np.abs(L[k + 1])
        if w[k + 1] != w[k]:
            m_w180 = m0 + (w180 - w[k]) * (m1 - m0) / (w[k + 1] - w[k])
        else:
            m_w180 = 0.5 * (m0 + m1)

        gm = 1.0 / max(float(m_w180), 1e-300)
        gm_db = 20.0 * np.log10(gm)
        has_w180 = True

    return {
        "pm_deg": pm_deg,
        "gm_db": gm_db,
        "ms": ms,
        "ms_db": ms_db,
        "has_wc": has_wc,
        "has_w180": has_w180,
        "wc": wc,
        "w180": w180,
        # debug helpers:
        "mag_db": mag_db,
        "phase_rad": phase,
        "L": L,
    }


def auto_frequency_grid_for_candidate(plant, Kp, Ti, Td, Tf,
                                      N1=300, N2=450,
                                      wmin1=1e-3, wmax1=1e3,
                                      wmin2=1e-5, wmax2=1e5,
                                      phase_near_deg=15.0):
    """
    Choose a frequency grid adaptively for a given (plant, PID) candidate.

    Strategy:
      1) Start with w in [wmin1, wmax1]
      2) If 0 dB crossover is missing but |L| indicates crossover likely outside range,
         OR if -180° crossing is missing but phase at the upper end is close to -180°,
         then expand once to [wmin2, wmax2].
      3) Return chosen w and the metrics computed on that w.

    This keeps runtime bounded (max 2 evaluations) and avoids hard-coded "10^3"
    assumptions while remaining cheap compared to time-domain simulation.
    """
    w1 = np.logspace(np.log10(wmin1), np.log10(wmax1), N1)
    m1 = compute_loop_metrics_single(plant, Kp, Ti, Td, Tf, w1)

    # Decide whether to expand the range once
    expand = False

    # (A) PM missing: maybe crossover outside range?
    # If |L| at low end and high end are both on the same side of 1, you might have missed it.
    # - if |L|_high > 1 -> crossover likely above wmax
    # - if |L|_low  < 1 -> crossover likely below wmin
    absL = np.abs(m1["L"])
    if not m1["has_wc"]:
        if absL[-1] > 1.0 or absL[0] < 1.0:
            expand = True

    # (B) GM missing: only expand if phase at high end is "near" -180°
    if not m1["has_w180"]:
        phase_end = m1["phase_rad"][-1]
        # near -pi within threshold (in radians)
        near = np.deg2rad(phase_near_deg)
        if abs(phase_end - (-np.pi)) <= near:
            expand = True

    if not expand:
        return w1, m1

    w2 = np.logspace(np.log10(wmin2), np.log10(wmax2), N2)
    m2 = compute_loop_metrics_single(plant, Kp, Ti, Td, Tf, w2)
    return w2, m2


def main():
    print("=== Frequency Metrics Test + Bode (adaptive grid) ===")

    # Plant: G(s)=1 / (s^2 + 2s + 1)
    plant = Plant(num=[23040], den=[1,9.6,2304])

    # Test-PID (frei anpassen)
    Kp = 9.79
    Ti = 0.49
    Td = 0.005
    Tf = 2.4e-5

    # Adaptive frequency grid selection + metrics
    w, metrics = auto_frequency_grid_for_candidate(plant, Kp, Ti, Td, Tf)

    print("\n--- Metrics ---")
    print(f"Grid: w in [{w[0]:.3g}, {w[-1]:.3g}] rad/s with N={len(w)}")
    print(f"PM  [deg]: {metrics['pm_deg']:.3f}   (has_wc={metrics['has_wc']}, wc={metrics['wc']:.6g} rad/s)")
    print(f"GM  [dB ]: {metrics['gm_db']:.3f}   (has_w180={metrics['has_w180']}, w180={metrics['w180']:.6g} rad/s)")
    print(f"Ms  [lin]: {metrics['ms']:.6f}   (= {metrics['ms_db']:.3f} dB)")

    # Bode aus deinem utils.bode_plot (mit gleichem w)
    pid = PIDClosedLoop(plant, Kp=Kp, Ti=Ti, Td=Td)
    pid.set_filter(Tf=Tf)

    systems_for_bode = {
        #"Plant G": plant.system,
        #"Controller C": pid.controller,
        "Open Loop L=C*G": (lambda s: pid.controller(s) * plant.system(s)),
        "Sensitivity S=1/(1+L)": (lambda s: 1.0 / (1.0 + pid.controller(s) * plant.system(s))),
    }

    bode_plot(systems_for_bode, omega=w, title="Bode (adaptive grid)")
    plt.show()


if __name__ == "__main__":
    main()