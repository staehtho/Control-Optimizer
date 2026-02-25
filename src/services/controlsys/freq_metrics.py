# src/services/controlsys/freq_metrics.py
from __future__ import annotations

import numpy as np


def pid_controller_freq_response(Kp, Ti, Td, Tf, s):
    """Compute the frequency response of a PID controller with derivative filter.

    The controller has the transfer function:

        C(s) = Kp * (1 + 1/(Ti*s) + (Td*s)/(Tf*s + 1))

    Args:
        Kp (float or ndarray): Proportional gain.
        Ti (float or ndarray): Integral time constant.
        Td (float or ndarray): Derivative time constant.
        Tf (float): Derivative filter time constant.
        s (complex ndarray): Complex frequency values (typically 1j * w).

    Returns:
        complex ndarray: Frequency response C(s) evaluated at each s.
    """
    return Kp * (1.0 + 1.0 / (Ti * s) + (Td * s) / (Tf * s + 1.0))


def _interp_x_at_y(x0, y0, x1, y1, y_target):
    """Linearly interpolate the x-value where y reaches a target value.

    Assumes a linear variation between the two points (x0, y0) and (x1, y1).

    Args:
        x0 (float): First x-coordinate.
        y0 (float): First y-coordinate.
        x1 (float): Second x-coordinate.
        y1 (float): Second y-coordinate.
        y_target (float): Target y-value to interpolate at.

    Returns:
        float: Interpolated x-value where y equals y_target.
            If y0 == y1, returns the midpoint of x0 and x1.
    """
    if y1 == y0:
        return 0.5 * (x0 + x1)
    return x0 + (y_target - y0) * (x1 - x0) / (y1 - y0)


def _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w):
    """Compute PM/GM/Ms for a batch on a given frequency grid (no adaptive expansion)."""
    w = np.asarray(w, dtype=float)
    s = 1j * w  # (N,)

    # Plant FRF once
    G = plant.system(s)  # (N,)

    # Ensure 1D arrays length P
    Kp = np.asarray(Kp, dtype=float).reshape(-1)
    Ti = np.asarray(Ti, dtype=float).reshape(-1)
    Td = np.asarray(Td, dtype=float).reshape(-1)
    Tf = np.asarray(Tf, dtype=float).reshape(-1)
    P = Kp.shape[0]

    # Controller FRF for all candidates: (P,N)
    C = pid_controller_freq_response(Kp[:, None], Ti[:, None], Td[:, None], Tf[:, None], s[None, :])

    # Open loop and sensitivity
    L = C * G[None, :]
    S = 1.0 / (1.0 + L)

    ms = np.max(np.abs(S), axis=1)  # (P,)

    mag_db = 20.0 * np.log10(np.maximum(np.abs(L), 1e-300))  # (P,N)
    phase = np.unwrap(np.angle(L), axis=1)  # (P,N) rad

    pm_deg = np.full(P, np.nan, dtype=float)
    gm_db = np.full(P, np.inf, dtype=float)
    wc = np.full(P, np.nan, dtype=float)
    w180 = np.full(P, np.nan, dtype=float)
    has_wc = np.zeros(P, dtype=bool)
    has_w180 = np.zeros(P, dtype=bool)

    # ---- PM (0 dB crossover) ----
    target_mag_db = 0.0
    for i in range(P):
        y = mag_db[i]
        sign = np.sign(y - target_mag_db)
        idx = np.where(sign[:-1] * sign[1:] < 0)[0]
        if idx.size == 0:
            continue

        k = idx[0]  # first crossover
        wc_i = _interp_x_at_y(w[k], y[k], w[k + 1], y[k + 1], target_mag_db)

        # phase interpolation at wc
        ph0, ph1 = phase[i, k], phase[i, k + 1]
        if w[k + 1] != w[k]:
            ph_wc = ph0 + (wc_i - w[k]) * (ph1 - ph0) / (w[k + 1] - w[k])
        else:
            ph_wc = 0.5 * (ph0 + ph1)

        pm_deg[i] = 180.0 + np.degrees(ph_wc)
        wc[i] = wc_i
        has_wc[i] = True

    # ---- GM (-180° crossing) ----
    target_phase = -np.pi
    for i in range(P):
        ph = phase[i]
        signp = np.sign(ph - target_phase)
        idxp = np.where(signp[:-1] * signp[1:] < 0)[0]
        if idxp.size == 0:
            # Policy: GM missing => +inf, has_w180=False (OK for GM_min checks)
            continue

        k = idxp[0]
        w180_i = _interp_x_at_y(w[k], ph[k], w[k + 1], ph[k + 1], target_phase)

        m0, m1 = np.abs(L[i, k]), np.abs(L[i, k + 1])
        if w[k + 1] != w[k]:
            m_w180 = m0 + (w180_i - w[k]) * (m1 - m0) / (w[k + 1] - w[k])
        else:
            m_w180 = 0.5 * (m0 + m1)

        gm = 1.0 / max(float(m_w180), 1e-300)
        gm_db[i] = 20.0 * np.log10(gm)
        w180[i] = w180_i
        has_w180[i] = True

    return {
        "pm_deg": pm_deg,
        "gm_db": gm_db,
        "ms": ms,
        "has_wc": has_wc,
        "has_w180": has_w180,
        "wc": wc,
        "w180": w180,
        # debug helpers (optional):
        "w": w,
        "mag_db": mag_db,
        "phase_rad": phase,
        "absL": np.abs(L),
    }


def compute_loop_metrics_batch(
    plant,
    Kp,
    Ti,
    Td,
    Tf,
    w: np.ndarray | None = None,
    *,
    adaptive_range: bool = True,
    N1: int = 300,
    wmin1: float = 1e-3,
    wmax1: float = 1e3,
    N2: int = 450,
    wmin2: float = 1e-5,
    wmax2: float = 1e5,
    phase_near_deg: float = 15.0,
):
    """Compute frequency-domain robustness metrics for a batch of PID parameter sets.

    Evaluates L(s)=C(s)G(s) and extracts:
      - PM (deg) at |L(jw)|=1 (0 dB crossover)
      - GM (dB) at angle(L)=-180° (phase crossover)
      - Ms (linear) = max |S(jw)| with S = 1/(1+L)

    Policies:
      - PM missing (no 0 dB crossover): has_wc=False (treat as infeasible)
      - GM missing (no -180° crossing): gm_db=+inf (OK for GM_min)

    Adaptive range (if enabled):
      - First evaluates on [wmin1, wmax1].
      - If it looks likely that wc or w180 lie outside the window for any candidate,
        expands once to [wmin2, wmax2] and recomputes (bounded runtime: max 2 runs).

    Args:
        plant: Plant instance with plant.system(s) vectorized over s.
        Kp, Ti, Td, Tf: Arrays of length P.
        w: Optional explicit frequency grid. If provided, adaptive_range is ignored.
        adaptive_range: Enable one-step range expansion.
        N1, wmin1, wmax1: Initial grid definition.
        N2, wmin2, wmax2: Expanded grid definition (used only if needed).
        phase_near_deg: If GM crossing is missing, expand only if phase at wmax1 is within
            this many degrees of -180° (to avoid pointless expansions).

    Returns:
        dict[str, np.ndarray]: Metrics arrays of length P (plus optional debug arrays).
    """
    if w is not None:
        return _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w)

    # --- pass 1: initial grid ---
    w1 = np.logspace(np.log10(wmin1), np.log10(wmax1), N1)
    m1 = _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w1)

    if not adaptive_range:
        return m1

    # Decide if we need expansion (once), based on ANY candidate needing it
    expand = False

    absL1 = m1["absL"]  # (P,N1)
    has_wc = m1["has_wc"]
    has_w180 = m1["has_w180"]
    phase1 = m1["phase_rad"]  # (P,N1)

    # (A) PM missing: likely crossover outside if |L| at high end still >1 OR at low end already <1
    #     (same idea as single-candidate test, but vectorized over P)
    if np.any(~has_wc):
        need = (~has_wc) & ((absL1[:, -1] > 1.0) | (absL1[:, 0] < 1.0))
        if np.any(need):
            expand = True

    # (B) GM missing: expand only if phase at high end is near -180° for at least one candidate
    if not expand and np.any(~has_w180):
        near = np.deg2rad(phase_near_deg)
        phase_end = phase1[:, -1]
        need = (~has_w180) & (np.abs(phase_end - (-np.pi)) <= near)
        if np.any(need):
            expand = True

    if not expand:
        return m1

    # --- pass 2: expanded grid ---
    w2 = np.logspace(np.log10(wmin2), np.log10(wmax2), N2)
    m2 = _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w2)
    return m2