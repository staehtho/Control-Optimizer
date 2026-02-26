# src/services/controlsys/freq_metrics.py
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


def pid_controller_freq_response(
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
    s: np.ndarray,
) -> np.ndarray:
    """Computes the frequency response of a PID controller with derivative filter.

    The controller transfer function is:

        C(s) = Kp * (1 + 1/(Ti*s) + (Td*s)/(Tf*s + 1))

    This function is vectorized and supports broadcasting. Typical usage within
    batch evaluation:

        C = pid_controller_freq_response(Kp[:, None], Ti[:, None], Td[:, None],
                                         Tf[:, None], s[None, :])

    Args:
        Kp: Proportional gain(s). Shape must be broadcastable to `s`.
        Ti: Integral time constant(s). Shape must be broadcastable to `s`.
        Td: Derivative time constant(s). Shape must be broadcastable to `s`.
        Tf: Derivative filter time constant(s). Shape must be broadcastable to `s`.
        s: Complex frequency points (e.g., 1j * omega). Typically shape (N,).

    Returns:
        Complex frequency response C(s) evaluated at `s` with broadcasted shape.

    Notes:
        - Ti must be > 0 for physical PID behavior. If Ti is extremely small,
          numerical overflow may occur; higher-level bounds should prevent that.
    """
    return Kp * (1.0 + 1.0 / (Ti * s) + (Td * s) / (Tf * s + 1.0))


def _interp_x_at_y(x0: float, y0: float, x1: float, y1: float, y_target: float) -> float:
    """Linearly interpolates the x-location where y crosses a target value.

    Args:
        x0: First x-coordinate.
        y0: First y-coordinate.
        x1: Second x-coordinate.
        y1: Second y-coordinate.
        y_target: Target y-value.

    Returns:
        Interpolated x-value where y equals y_target. If y0 == y1, returns the midpoint.
    """
    if y1 == y0:
        return 0.5 * (x0 + x1)
    return x0 + (y_target - y0) * (x1 - x0) / (y1 - y0)


def _finite_guard_mask(L: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Builds a per-candidate validity mask based on finiteness of L and S.

    Args:
        L: Open-loop frequency response, shape (P, N).
        S: Sensitivity frequency response, shape (P, N).

    Returns:
        Boolean mask `ok_particles` of shape (P,) where True indicates that all
        frequencies for that candidate are finite (no NaN/Inf) in both L and S.

    Rationale:
        Plants with poles on the imaginary axis (or other numerical pathologies)
        can produce Inf/NaN at some frequencies. For robust optimization, those
        candidates should be treated as invalid/infeasible and must not enter
        phase unwrap or crossing detection logic.
    """
    finite_L = np.isfinite(L.real) & np.isfinite(L.imag)
    finite_S = np.isfinite(S.real) & np.isfinite(S.imag)
    return np.all(finite_L, axis=1) & np.all(finite_S, axis=1)


def _compute_metrics_on_grid(
    plant: Any,
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
    w: np.ndarray,
) -> Dict[str, np.ndarray]:
    """Computes PM/GM/Ms on a fixed frequency grid for a batch of PID candidates.

    This function does not perform adaptive range expansion. It evaluates:

      - Open-loop: L(jw) = C(jw) * G(jw)
      - Sensitivity: S(jw) = 1 / (1 + L(jw))
      - Phase margin PM at the first |L|=1 (0 dB) crossover.
      - Gain margin GM at the first phase=-180° crossover.
      - Robustness Ms = max_w |S(jw)| (linear).

    Policies:
      - PM missing (no 0 dB crossover): has_wc=False, pm_deg=NaN  (=> infeasible upstream)
      - GM missing (no -180° crossing): gm_db=+inf              (=> OK for GM_min checks)
      - Non-finite anywhere (L or S has NaN/Inf): mark candidate invalid:
            ok_particles=False, has_wc=False, pm_deg=NaN, ms=+inf, gm_db=+inf

    Args:
        plant: Plant instance with `plant.system(s)` vectorized over complex s.
        Kp: Proportional gains, shape (P,).
        Ti: Integral time constants, shape (P,).
        Td: Derivative time constants, shape (P,).
        Tf: Derivative filter time constants, shape (P,).
        w: Frequency grid (rad/s), shape (N,).

    Returns:
        Dictionary containing metrics arrays of length P, plus optional debug arrays:
          - pm_deg, gm_db, ms
          - has_wc, has_w180
          - wc, w180
          - w, mag_db, phase_rad, absL
          - ok_particles
    """
    w = np.asarray(w, dtype=float)
    s = 1j * w  # (N,)

    # Normalize parameter arrays to shape (P,)
    Kp = np.asarray(Kp, dtype=float).reshape(-1)
    Ti = np.asarray(Ti, dtype=float).reshape(-1)
    Td = np.asarray(Td, dtype=float).reshape(-1)
    Tf = np.asarray(Tf, dtype=float).reshape(-1)

    P = Kp.shape[0]
    N = w.shape[0]

    # Evaluate plant once on the grid; allow Inf/NaN to appear, we'll guard downstream.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        G = plant.system(s)  # (N,)

        # Controller response for all candidates: (P, N)
        C = pid_controller_freq_response(
            Kp[:, None],
            Ti[:, None],
            Td[:, None],
            Tf[:, None],
            s[None, :],
        )

        # Open-loop and sensitivity: (P, N)
        L = C * G[None, :]
        S = 1.0 / (1.0 + L)

    ok_particles = _finite_guard_mask(L, S)
    good_idx = np.where(ok_particles)[0]

    # Allocate outputs with "invalid/infeasible" defaults.
    pm_deg = np.full(P, np.nan, dtype=float)
    gm_db = np.full(P, np.inf, dtype=float)
    ms = np.full(P, np.inf, dtype=float)

    wc = np.full(P, np.nan, dtype=float)
    w180 = np.full(P, np.nan, dtype=float)
    has_wc = np.zeros(P, dtype=bool)
    has_w180 = np.zeros(P, dtype=bool)

    # Debug arrays (keep stable shapes for diagnostics)
    absL = np.full((P, N), np.nan, dtype=float)
    mag_db = np.full((P, N), np.nan, dtype=float)
    phase_rad = np.full((P, N), np.nan, dtype=float)

    if good_idx.size == 0:
        return {
            "pm_deg": pm_deg,
            "gm_db": gm_db,
            "ms": ms,
            "has_wc": has_wc,
            "has_w180": has_w180,
            "wc": wc,
            "w180": w180,
            "w": w,
            "mag_db": mag_db,
            "phase_rad": phase_rad,
            "absL": absL,
            "ok_particles": ok_particles,
        }

    # Work only on finite candidates.
    Lg = L[good_idx]  # (Pg, N)
    Sg = S[good_idx]  # (Pg, N)

    absLg = np.abs(Lg)
    absL[good_idx] = absLg

    # Ms: peak sensitivity (linear)
    ms_good = np.max(np.abs(Sg), axis=1)
    ms[good_idx] = ms_good

    # Magnitude/phase
    mag_db_good = 20.0 * np.log10(np.maximum(absLg, 1e-300))
    mag_db[good_idx] = mag_db_good

    phase_good = np.unwrap(np.angle(Lg), axis=1)
    phase_rad[good_idx] = phase_good

    # ---- Phase Margin (PM) at first 0 dB crossover ----
    target_mag_db = 0.0
    for local_i, i in enumerate(good_idx):
        y = mag_db_good[local_i]  # (N,)
        sign = np.sign(y - target_mag_db)
        idx = np.where(sign[:-1] * sign[1:] < 0)[0]
        if idx.size == 0:
            continue

        k = int(idx[0])
        wc_i = _interp_x_at_y(w[k], float(y[k]), w[k + 1], float(y[k + 1]), target_mag_db)

        ph0, ph1 = float(phase_good[local_i, k]), float(phase_good[local_i, k + 1])
        if w[k + 1] != w[k]:
            ph_wc = ph0 + (wc_i - w[k]) * (ph1 - ph0) / (w[k + 1] - w[k])
        else:
            ph_wc = 0.5 * (ph0 + ph1)

        pm_deg[i] = 180.0 + np.degrees(ph_wc)
        wc[i] = wc_i
        has_wc[i] = True

    # ---- Gain Margin (GM) at first -180° phase crossover ----
    target_phase = -np.pi
    for local_i, i in enumerate(good_idx):
        ph = phase_good[local_i]  # (N,)
        signp = np.sign(ph - target_phase)
        idxp = np.where(signp[:-1] * signp[1:] < 0)[0]
        if idxp.size == 0:
            # Policy: GM missing => +inf
            continue

        k = int(idxp[0])
        w180_i = _interp_x_at_y(w[k], float(ph[k]), w[k + 1], float(ph[k + 1]), target_phase)

        m0, m1 = float(absLg[local_i, k]), float(absLg[local_i, k + 1])
        if w[k + 1] != w[k]:
            m_w180 = m0 + (w180_i - w[k]) * (m1 - m0) / (w[k + 1] - w[k])
        else:
            m_w180 = 0.5 * (m0 + m1)

        gm = 1.0 / max(m_w180, 1e-300)
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
        "w": w,
        "mag_db": mag_db,
        "phase_rad": phase_rad,
        "absL": absL,
        "ok_particles": ok_particles,
    }


def compute_loop_metrics_batch(
    plant: Any,
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
    w: Optional[np.ndarray] = None,
    *,
    adaptive_range: bool = True,
    N1: int = 300,
    wmin1: float = 1e-3,
    wmax1: float = 1e3,
    N2: int = 450,
    wmin2: float = 1e-5,
    wmax2: float = 1e5,
    phase_near_deg: float = 15.0,
) -> Dict[str, np.ndarray]:
    """Computes frequency-domain robustness metrics for a batch of PID candidates.

    It evaluates open-loop and sensitivity frequency responses and computes:
      - Phase margin (PM) in degrees at the first 0 dB crossover.
      - Gain margin (GM) in dB at the first -180° phase crossover.
      - Sensitivity peak Ms (linear), Ms = max_w |S(jw)|.

    Policies:
      - PM missing (no 0 dB crossover): has_wc=False, pm_deg=NaN  (treat as infeasible)
      - GM missing (no -180° crossing): gm_db=+inf              (OK for GM_min checks)
      - Non-finite FRF anywhere (L or S contains NaN/Inf):
            ok_particles=False, has_wc=False, pm_deg=NaN, ms=+inf, gm_db=+inf

    Adaptive range (bounded to max 2 evaluations):
      1) Evaluate on [wmin1, wmax1] with N1 points.
      2) If any *valid* candidate suggests wc/w180 lie outside this window, evaluate once
         on [wmin2, wmax2] with N2 points.

    Expansion triggers (evaluated on pass 1):
      - PM missing and (|L| at high end > 1) OR (|L| at low end < 1)
      - GM missing and phase at high end is within `phase_near_deg` of -180°

    Args:
        plant: Plant instance with `plant.system(s)` vectorized over complex s.
        Kp: Proportional gains, shape (P,).
        Ti: Integral time constants, shape (P,).
        Td: Derivative time constants, shape (P,).
        Tf: Derivative filter time constants, shape (P,).
        w: Optional explicit frequency grid. If provided, `adaptive_range` is ignored.
        adaptive_range: If True, allow one-step frequency-range expansion.
        N1: Number of frequency points in the initial grid.
        wmin1: Minimum rad/s for the initial grid.
        wmax1: Maximum rad/s for the initial grid.
        N2: Number of frequency points in the expanded grid.
        wmin2: Minimum rad/s for the expanded grid.
        wmax2: Maximum rad/s for the expanded grid.
        phase_near_deg: Threshold (degrees) for deciding whether to expand for GM.

    Returns:
        Dict mapping metric names to arrays of length P, plus debug arrays:
          - pm_deg: Phase margin in degrees (NaN if missing/invalid).
          - gm_db: Gain margin in dB (+inf if missing/invalid).
          - ms: Sensitivity peak (linear) (+inf if invalid).
          - has_wc: Whether a 0 dB crossover was found.
          - has_w180: Whether a -180° crossing was found.
          - wc: Gain crossover frequency (rad/s) or NaN.
          - w180: Phase crossover frequency (rad/s) or NaN.
          - w: The frequency grid actually used (w1 or w2 or provided w).
          - mag_db, phase_rad, absL: Debug arrays with shape (P, N).
          - ok_particles: Boolean mask indicating finite candidates on the evaluated grid.
    """
    if w is not None:
        return _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w)

    # Pass 1: initial grid
    w1 = np.logspace(np.log10(wmin1), np.log10(wmax1), N1)
    m1 = _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w1)

    if not adaptive_range:
        return m1

    # Decide whether to expand once (based on any *valid* candidate needing it)
    okp = m1.get("ok_particles", np.ones_like(m1["has_wc"], dtype=bool))
    has_wc = m1["has_wc"]
    has_w180 = m1["has_w180"]
    absL1 = m1["absL"]         # (P, N1) may contain NaN for invalid candidates
    phase1 = m1["phase_rad"]   # (P, N1) may contain NaN for invalid candidates

    expand = False

    # (A) PM missing: likely crossover outside if |L| at high end still > 1 OR at low end already < 1
    if np.any(okp & (~has_wc)):
        need = (okp & (~has_wc)) & ((absL1[:, -1] > 1.0) | (absL1[:, 0] < 1.0))
        if np.any(need):
            expand = True

    # (B) GM missing: expand only if phase at high end is near -180° for at least one ok candidate
    if (not expand) and np.any(okp & (~has_w180)):
        near = np.deg2rad(phase_near_deg)
        phase_end = phase1[:, -1]
        need = (okp & (~has_w180)) & (np.abs(phase_end - (-np.pi)) <= near)
        if np.any(need):
            expand = True

    if not expand:
        return m1

    # Pass 2: expanded grid
    w2 = np.logspace(np.log10(wmin2), np.log10(wmax2), N2)
    return _compute_metrics_on_grid(plant, Kp, Ti, Td, Tf, w2)