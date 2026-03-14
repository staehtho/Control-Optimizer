# src/services/controlsys/freq_metrics.py
from __future__ import annotations

from typing import Any

import numpy as np


def pid_controller_freq_response(
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
    s: np.ndarray,
) -> np.ndarray:
    """Compute the frequency response of a PID controller with derivative filter.

    The controller transfer function is:

        C(s) = Kp * (1 + 1/(Ti*s) + (Td*s)/(Tf*s + 1))

    This function is vectorized and supports broadcasting. Typical usage within
    batch evaluation:

        C = pid_controller_freq_response(
            Kp[:, None],
            Ti[:, None],
            Td[:, None],
            Tf[:, None],
            s[None, :],
        )

    Args:
        Kp: Proportional gain(s). Shape must be broadcastable to ``s``.
        Ti: Integral time constant(s). Shape must be broadcastable to ``s``.
        Td: Derivative time constant(s). Shape must be broadcastable to ``s``.
        Tf: Derivative filter time constant(s). Shape must be broadcastable to ``s``.
        s: Complex frequency points (for example ``1j * omega``).

    Returns:
        Complex controller response ``C(s)`` with broadcasted shape.
    """
    return Kp * (1.0 + 1.0 / (Ti * s) + (Td * s) / (Tf * s + 1.0))


def _interp_x_at_y(x0: float, y0: float, x1: float, y1: float, y_target: float) -> float:
    """Linearly interpolate the x-location where y crosses a target value."""
    if y1 == y0:
        return 0.5 * (x0 + x1)
    return x0 + (y_target - y0) * (x1 - x0) / (y1 - y0)


def _outermost_crossing_batch_x(
    x: np.ndarray,
    y: np.ndarray,
    target: float,
    *,
    atol: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Find the outermost / highest-frequency crossing for each row of ``y``.

    A near-exact sample hit counts as a valid crossing. When multiple crossings
    exist, the highest-frequency valid one is returned. On a target plateau,
    the rightmost sample on that plateau wins.

    Args:
        x: Sample locations of shape ``(N,)``, ordered from low to high frequency.
        y: Sample values of shape ``(P, N)``.
        target: Target value to cross.
        atol: Absolute tolerance for direct sample hits.

    Returns:
        Tuple ``(found, x_cross, k_left)`` with shape ``(P,)`` each, where
        ``k_left`` is the left interval index used for interpolation or
        bracketing. Undefined rows use ``found=False``, ``x_cross=NaN``,
        ``k_left=-1``.
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64)
    if y.ndim == 1:
        y = y[None, :]

    if x.shape[0] != y.shape[1]:
        raise ValueError("x length must match the last dimension of y.")
    if x.shape[0] < 2:
        P = y.shape[0]
        return (
            np.zeros(P, dtype=np.bool_),
            np.full(P, np.nan, dtype=np.float64),
            np.full(P, -1, dtype=np.int64),
        )

    target = float(target)

    y0 = y[:, :-1]
    y1 = y[:, 1:]

    hit0 = np.isclose(y0, target, atol=atol, rtol=0.0)
    hit1 = np.isclose(y1, target, atol=atol, rtol=0.0)

    d0 = y0 - target
    d1 = y1 - target
    sign_change = (d0 * d1) < 0.0

    candidates = hit0 | hit1 | sign_change
    found = np.any(candidates, axis=1)

    P, M = candidates.shape
    last_from_right = np.argmax(candidates[:, ::-1], axis=1)
    k_left = (M - 1) - last_from_right
    k_left = np.where(found, k_left, -1).astype(np.int64, copy=False)

    x_cross = np.full(P, np.nan, dtype=np.float64)
    if not np.any(found):
        return found, x_cross, k_left

    rows = np.where(found)[0]
    k = k_left[rows]

    y0_sel = y0[rows, k]
    y1_sel = y1[rows, k]
    hit0_sel = hit0[rows, k]
    hit1_sel = hit1[rows, k]

    x0_sel = x[k]
    x1_sel = x[k + 1]

    interp_sel = np.where(
        y1_sel == y0_sel,
        0.5 * (x0_sel + x1_sel),
        x0_sel + (target - y0_sel) * (x1_sel - x0_sel) / (y1_sel - y0_sel),
    )

    x_cross_sel = np.where(
        hit1_sel,
        x1_sel,
        np.where(hit0_sel, x0_sel, interp_sel),
    )
    x_cross[rows] = x_cross_sel

    return found, x_cross, k_left


def _finite_complex_mask(z: np.ndarray) -> np.ndarray:
    """Return per-entry finiteness mask for a complex array."""
    return np.isfinite(z.real) & np.isfinite(z.imag)


def _normalize_pid_params(
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Normalize PID parameter arrays to shape (P,) and dtype float64."""
    Kp = np.asarray(Kp, dtype=np.float64).reshape(-1)
    Ti = np.asarray(Ti, dtype=np.float64).reshape(-1)
    Td = np.asarray(Td, dtype=np.float64).reshape(-1)
    Tf = np.asarray(Tf, dtype=np.float64).reshape(-1)

    P = Kp.shape[0]
    if not (Ti.shape[0] == P and Td.shape[0] == P and Tf.shape[0] == P):
        raise ValueError("Kp, Ti, Td, and Tf must all have the same batch length.")

    return Kp, Ti, Td, Tf


def compute_loop_metrics_batch_from_frf(
    G: np.ndarray,
    w: np.ndarray,
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute PM, GM, and Ms for a batch of PID candidates on a fixed grid.

    This is the single active implementation used by the optimizer. It expects
    the plant frequency response ``G(jw)`` on a predefined frequency grid and
    evaluates all PID candidates against that same grid.

    Policies:
      - Missing 0 dB crossover: ``has_wc=False``, ``pm_deg=NaN``.
      - Missing -180° crossover: ``has_w180=False``, ``gm_db=+inf``.
      - Any non-finite value in ``L`` or ``S`` anywhere on the grid:
            candidate is invalid, ``numerically_valid_particles=False``, ``has_wc=False``,
            ``has_w180=False``, ``pm_deg=NaN``, ``gm_db=+inf``, ``ms=+inf``.
      - When multiple crossings exist, the outermost / highest-frequency
        valid crossing is used.

    Args:
        G: Plant frequency response ``G(jw)``, shape ``(N,)``.
        w: Frequency grid in rad/s, shape ``(N,)``.
        Kp, Ti, Td, Tf: PID parameters, shape ``(P,)``.

    Returns:
        Dictionary containing only the metrics used by the optimizer / callers:
          - ``pm_deg``, ``gm_db``, ``ms``
          - ``has_wc``, ``has_w180``
          - ``wc``, ``w180``
          - ``numerically_valid_particles``
    """
    w = np.asarray(w, dtype=np.float64).reshape(-1)
    G = np.asarray(G, dtype=np.complex128).reshape(-1)

    if w.ndim != 1 or G.ndim != 1:
        raise ValueError("w and G must be one-dimensional arrays.")
    if w.shape[0] != G.shape[0]:
        raise ValueError("w and G must have the same length.")

    Kp, Ti, Td, Tf = _normalize_pid_params(Kp, Ti, Td, Tf)

    P = Kp.shape[0]
    s = 1j * w

    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        C = pid_controller_freq_response(
            Kp[:, None],
            Ti[:, None],
            Td[:, None],
            Tf[:, None],
            s[None, :],
        )
        L = C * G[None, :]
        S = 1.0 / (1.0 + L)

    finite_L = _finite_complex_mask(L)
    finite_S = _finite_complex_mask(S)

    numerically_valid_particles = np.all(finite_L, axis=1) & np.all(finite_S, axis=1)
    good_idx = np.where(numerically_valid_particles)[0]

    # Default outputs correspond to invalid / infeasible candidates.
    pm_deg = np.full(P, np.nan, dtype=np.float64)
    gm_db = np.full(P, np.inf, dtype=np.float64)
    ms = np.full(P, np.inf, dtype=np.float64)

    wc = np.full(P, np.nan, dtype=np.float64)
    w180 = np.full(P, np.nan, dtype=np.float64)
    has_wc = np.zeros(P, dtype=np.bool_)
    has_w180 = np.zeros(P, dtype=np.bool_)

    if good_idx.size == 0:
        return {
            "pm_deg": pm_deg,
            "gm_db": gm_db,
            "ms": ms,
            "has_wc": has_wc,
            "has_w180": has_w180,
            "wc": wc,
            "w180": w180,
            "numerically_valid_particles": numerically_valid_particles,
        }

    Lg = L[good_idx]
    Sg = S[good_idx]

    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        ms_good = np.max(np.abs(Sg), axis=1)
        absLg = np.abs(Lg)
        mag_db_good = 20.0 * np.log10(np.maximum(absLg, 1e-300))

    phase_good = np.unwrap(np.angle(Lg), axis=1)

    ms[good_idx] = ms_good

    # ---- PM: outermost / highest-frequency 0 dB crossover ----
    found_wc_local, wc_local, k_wc_local = _outermost_crossing_batch_x(
        w,
        mag_db_good,
        0.0,
        atol=1e-12,
    )
    pm_rows = np.where(found_wc_local)[0]
    if pm_rows.size:
        k = k_wc_local[pm_rows]
        wc_rows = wc_local[pm_rows]

        w0 = w[k]
        w1 = w[k + 1]
        ph0 = phase_good[pm_rows, k]
        ph1 = phase_good[pm_rows, k + 1]

        ph_wc = np.where(
            w1 != w0,
            ph0 + (wc_rows - w0) * (ph1 - ph0) / (w1 - w0),
            0.5 * (ph0 + ph1),
        )

        global_rows = good_idx[pm_rows]
        pm_deg[global_rows] = 180.0 + np.degrees(ph_wc)
        wc[global_rows] = wc_rows
        has_wc[global_rows] = True

    # ---- GM: outermost / highest-frequency -180° crossover ----
    found_w180_local, w180_local, k_w180_local = _outermost_crossing_batch_x(
        w,
        phase_good,
        -np.pi,
        atol=1e-9,
    )
    gm_rows = np.where(found_w180_local)[0]
    if gm_rows.size:
        k = k_w180_local[gm_rows]
        w180_rows = w180_local[gm_rows]

        w0 = w[k]
        w1 = w[k + 1]
        m0 = absLg[gm_rows, k]
        m1 = absLg[gm_rows, k + 1]

        m_w180 = np.where(
            w1 != w0,
            m0 + (w180_rows - w0) * (m1 - m0) / (w1 - w0),
            0.5 * (m0 + m1),
        )

        gm = 1.0 / np.maximum(m_w180, 1e-300)
        global_rows = good_idx[gm_rows]
        gm_db[global_rows] = 20.0 * np.log10(gm)
        w180[global_rows] = w180_rows
        has_w180[global_rows] = True

    return {
        "pm_deg": pm_deg,
        "gm_db": gm_db,
        "ms": ms,
        "has_wc": has_wc,
        "has_w180": has_w180,
        "wc": wc,
        "w180": w180,
        "numerically_valid_particles": numerically_valid_particles,
    }


def compute_loop_metrics_batch(
    plant: Any,
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
    w: np.ndarray,
) -> dict[str, np.ndarray]:
    """Convenience wrapper that evaluates the plant FRF internally."""
    w = np.asarray(w, dtype=np.float64).reshape(-1)
    s = 1j * w

    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        G = plant.system(s)

    return compute_loop_metrics_batch_from_frf(
        G=G,
        w=w,
        Kp=Kp,
        Ti=Ti,
        Td=Td,
        Tf=Tf,
    )
