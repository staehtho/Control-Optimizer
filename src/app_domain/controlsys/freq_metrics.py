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
    """Compute the frequency response of an ideal/ISA PID controller with derivative filter.

    The controller transfer function is:

        C(s) = Kp * (1 + 1/(Ti*s) + (Td*s)/(Tf*s + 1))

    This module expects the ISA time-constant parameterization ``(Kp, Ti, Td, Tf)``.
    It does not use product-series PID semantics.

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


def _find_crossings_1d(
    x: np.ndarray,
    y: np.ndarray,
    target: float,
    *,
    atol: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    """Find all crossings of ``y`` with ``target`` on a 1D grid.

    A near-exact sample hit counts as a valid crossing. Consecutive duplicate
    crossings caused by a target plateau are collapsed so that each distinct
    crossing location appears only once.

    Args:
        x: Sample locations of shape ``(N,)``.
        y: Sample values of shape ``(N,)``.
        target: Target value to cross.
        atol: Absolute tolerance for direct sample hits.

    Returns:
        Tuple ``(x_cross, k_left)``. ``x_cross`` contains all crossing
        locations, and ``k_left`` contains the corresponding left interval
        indices used for interpolation.
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)

    if x.shape[0] != y.shape[0]:
        raise ValueError("x and y must have the same length.")
    if x.shape[0] < 2:
        return (
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    target = float(target)

    y0 = y[:-1]
    y1 = y[1:]

    hit0 = np.isclose(y0, target, atol=atol, rtol=0.0)
    hit1 = np.isclose(y1, target, atol=atol, rtol=0.0)

    d0 = y0 - target
    d1 = y1 - target
    sign_change = (d0 * d1) < 0.0

    candidates = hit0 | hit1 | sign_change
    if not np.any(candidates):
        return (
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )

    k_left = np.flatnonzero(candidates).astype(np.int64, copy=False)

    y0_sel = y0[k_left]
    y1_sel = y1[k_left]
    hit0_sel = hit0[k_left]
    hit1_sel = hit1[k_left]

    x0_sel = x[k_left]
    x1_sel = x[k_left + 1]

    x_cross = np.empty_like(x0_sel)
    flat_mask = y1_sel == y0_sel
    x_cross[flat_mask] = 0.5 * (x0_sel[flat_mask] + x1_sel[flat_mask])
    non_flat_mask = ~flat_mask
    x_cross[non_flat_mask] = (
        x0_sel[non_flat_mask]
        + (target - y0_sel[non_flat_mask])
        * (x1_sel[non_flat_mask] - x0_sel[non_flat_mask])
        / (y1_sel[non_flat_mask] - y0_sel[non_flat_mask])
    )
    x_cross = np.where(
        hit1_sel,
        x1_sel,
        np.where(hit0_sel, x0_sel, x_cross),
    )

    if x_cross.size > 1:
        keep = np.ones(x_cross.shape[0], dtype=np.bool_)
        keep[1:] = x_cross[1:] != x_cross[:-1]
        x_cross = x_cross[keep]
        k_left = k_left[keep]

    return x_cross, k_left


def _interpolate_values_at_crossings(
    x: np.ndarray,
    y: np.ndarray,
    k_left: np.ndarray,
    x_cross: np.ndarray,
) -> np.ndarray:
    """Linearly interpolate ``y`` at crossing locations described by ``k_left``."""
    x0 = x[k_left]
    x1 = x[k_left + 1]
    y0 = y[k_left]
    y1 = y[k_left + 1]
    return np.where(
        x1 != x0,
        y0 + (x_cross - x0) * (y1 - y0) / (x1 - x0),
        0.5 * (y0 + y1),
    )


def _interpolate_crossings_batch(
    x: np.ndarray,
    y: np.ndarray,
    target: float,
    z: np.ndarray,
    *,
    atol: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Find and interpolate all crossings against one scalar target in batch form.

    Args:
        x: Sample locations of shape ``(N,)``.
        y: Sample values of shape ``(P, N)`` whose crossings are searched.
        target: Scalar target value to cross.
        z: Companion values of shape ``(P, N)`` to interpolate at the same
            crossing locations.
        atol: Absolute tolerance for direct sample hits.

    Returns:
        Tuple ``(candidate_mask, x_cross, z_cross)`` with shape ``(P, N-1)``
        each. Entries where ``candidate_mask`` is ``False`` are undefined in
        ``x_cross`` and ``z_cross`` and must be masked by the caller.
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)

    if y.ndim != 2 or z.ndim != 2:
        raise ValueError("y and z must be two-dimensional arrays.")
    if y.shape != z.shape:
        raise ValueError("y and z must have the same shape.")
    if x.shape[0] != y.shape[1]:
        raise ValueError("x length must match the last dimension of y and z.")

    y0 = y[:, :-1]
    y1 = y[:, 1:]
    z0 = z[:, :-1]
    z1 = z[:, 1:]

    x0 = np.broadcast_to(x[:-1], y0.shape)
    x1 = np.broadcast_to(x[1:], y0.shape)

    hit0 = np.isclose(y0, target, atol=atol, rtol=0.0)
    hit1 = np.isclose(y1, target, atol=atol, rtol=0.0)
    sign_change = ((y0 - target) * (y1 - target)) < 0.0
    candidates = hit0 | hit1 | sign_change

    x_cross = np.empty_like(y0)
    flat_mask = y1 == y0
    x_cross[flat_mask] = 0.5 * (x0[flat_mask] + x1[flat_mask])
    non_flat_mask = ~flat_mask
    x_cross[non_flat_mask] = (
        x0[non_flat_mask]
        + (target - y0[non_flat_mask])
        * (x1[non_flat_mask] - x0[non_flat_mask])
        / (y1[non_flat_mask] - y0[non_flat_mask])
    )
    x_cross = np.where(hit1, x1, np.where(hit0, x0, x_cross))

    z_cross = np.empty_like(z0)
    same_x_mask = x1 == x0
    z_cross[same_x_mask] = 0.5 * (z0[same_x_mask] + z1[same_x_mask])
    diff_x_mask = ~same_x_mask
    z_cross[diff_x_mask] = (
        z0[diff_x_mask]
        + (x_cross[diff_x_mask] - x0[diff_x_mask])
        * (z1[diff_x_mask] - z0[diff_x_mask])
        / (x1[diff_x_mask] - x0[diff_x_mask])
    )
    z_cross = np.where(hit1, z1, np.where(hit0, z0, z_cross))

    return candidates, x_cross, z_cross


def _select_worst_metric_batch(
    metric_candidates: np.ndarray,
    x_candidates: np.ndarray,
    candidate_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Select the smallest valid metric per row from batch candidate arrays.

    Args:
        metric_candidates: Candidate metric values of shape ``(P, M)``.
        x_candidates: Candidate x-locations of shape ``(P, M)``.
        candidate_mask: Boolean validity mask of shape ``(P, M)``.

    Returns:
        Tuple ``(found, best_x, best_metric)`` with shape ``(P,)`` each.
        Rows without valid candidates return ``found=False``, ``best_x=NaN``,
        and ``best_metric=+inf``.
    """
    masked_metric = np.where(candidate_mask, metric_candidates, np.inf)
    best_idx = np.argmin(masked_metric, axis=1)
    rows = np.arange(masked_metric.shape[0], dtype=np.int64)
    found = np.any(candidate_mask, axis=1)

    best_metric = np.where(found, masked_metric[rows, best_idx], np.inf)
    best_x = np.where(found, x_candidates[rows, best_idx], np.nan)
    return found, best_x, best_metric


def _compute_gain_margin_row(
    log_w: np.ndarray,
    phase_row: np.ndarray,
    mag_db_row: np.ndarray,
) -> tuple[bool, float, float]:
    """Compute the worst gain margin for one open-loop frequency response.

    This fallback path considers all odd negative phase targets reached by the
    unwrapped phase, i.e. ``-pi, -3pi, -5pi, ...``, and returns the smallest
    gain margin among them.
    """
    min_phase = float(np.min(phase_row))
    max_phase = float(np.max(phase_row))

    best_gm_db = np.inf
    best_log_w180 = np.nan
    found_any = False

    target = -np.pi
    while target >= min_phase - 1e-9:
        if target <= max_phase + 1e-9:
            log_w180, k_w180 = _find_crossings_1d(log_w, phase_row, target, atol=1e-9)
            if log_w180.size:
                mag_db_at_w180 = _interpolate_values_at_crossings(log_w, mag_db_row, k_w180, log_w180)
                gm_candidates_db = -mag_db_at_w180
                worst_idx = int(np.argmin(gm_candidates_db))
                worst_gm_db = float(gm_candidates_db[worst_idx])

                if (not found_any) or (worst_gm_db < best_gm_db):
                    best_gm_db = worst_gm_db
                    best_log_w180 = float(log_w180[worst_idx])
                    found_any = True

        target -= 2.0 * np.pi

    if not found_any:
        return False, np.nan, np.inf

    return True, float(np.exp(best_log_w180)), best_gm_db


def _finite_complex_mask(z: np.ndarray) -> np.ndarray:
    """Return per-entry finiteness mask for a complex array."""
    return np.isfinite(z.real) & np.isfinite(z.imag)


def compute_loop_metrics_batch_from_frf(
    G: np.ndarray,
    w: np.ndarray,
    Kp: np.ndarray,
    Ti: np.ndarray,
    Td: np.ndarray,
    Tf: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute loop stability metrics for a batch of ISA-form PID candidates.

    The plant response ``G(jw)`` is assumed to be precomputed on the
    frequency grid ``w``. All PID candidates are evaluated on that same grid
    using the ISA time-constant parameterization ``(Kp, Ti, Td, Tf)``.

    Computed outputs:
        - ``pm_deg``: worst phase margin in degrees
        - ``gm_db``: worst gain margin in dB
        - ``ms``: maximum sensitivity ``max |S(jw)|``
        - ``wc``: crossover frequency associated with the worst phase margin
        - ``w180``: crossover frequency associated with the worst gain margin
        - ``has_wc`` / ``has_w180``: crossover existence flags
        - ``numerically_valid_particles``: numerical validity flag

    Conventions:
        - If no 0 dB crossover exists, ``has_wc=False`` and ``pm_deg=NaN``.
        - If no odd negative phase crossover exists, ``has_w180=False`` and
          ``gm_db=+inf``.
        - If ``L`` or ``S`` contains any non-finite value on the grid, the
          candidate is treated as invalid. In that case:
          ``numerically_valid_particles=False``, ``has_wc=False``,
          ``has_w180=False``, ``pm_deg=NaN``, ``gm_db=+inf``, ``ms=+inf``.
        - If multiple 0 dB crossovers exist, the worst phase margin is used.
        - Gain margin is evaluated over all odd negative phase targets
          ``-pi, -3pi, -5pi, ...`` reached by the unwrapped phase, and the
          worst gain margin is used.
        - Crossover interpolation is performed on ``log(w)``.

    Args:
        G: Plant frequency response with shape ``(N,)``.
        w: Frequency grid in rad/s with shape ``(N,)``.
        Kp: Proportional gains with shape ``(P,)``.
        Ti: Integral time constants with shape ``(P,)``.
        Td: Derivative time constants with shape ``(P,)``.
        Tf: Derivative filter time constants with shape ``(P,)``.

    Returns:
        Dictionary with batch-wise metric arrays of shape ``(P,)``.
    """
    w = np.asarray(w, dtype=np.float64)
    G = np.asarray(G, dtype=np.complex128)

    if w.ndim != 1 or G.ndim != 1:
        raise ValueError("w and G must be one-dimensional arrays.")
    w = w.reshape(-1)
    G = G.reshape(-1)

    if w.shape[0] != G.shape[0]:
        raise ValueError("w and G must have the same length.")

    Kp = np.asarray(Kp, dtype=np.float64)
    Ti = np.asarray(Ti, dtype=np.float64)
    Td = np.asarray(Td, dtype=np.float64)
    Tf = np.asarray(Tf, dtype=np.float64)

    if Kp.ndim != 1 or Ti.ndim != 1 or Td.ndim != 1 or Tf.ndim != 1:
        raise ValueError("Kp, Ti, Td, and Tf must be one-dimensional arrays.")

    Kp = Kp.reshape(-1)
    Ti = Ti.reshape(-1)
    Td = Td.reshape(-1)
    Tf = Tf.reshape(-1)

    P = Kp.shape[0]
    if not (Ti.shape[0] == P and Td.shape[0] == P and Tf.shape[0] == P):
        raise ValueError("Kp, Ti, Td, and Tf must all have the same batch length.")

    s = 1j * w
    log_w = np.log(w)

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
    min_phase_good = np.min(phase_good, axis=1)

    ms[good_idx] = ms_good

    pm_mask, pm_log_wc, pm_phase_at_wc = _interpolate_crossings_batch(
        log_w,
        mag_db_good,
        0.0,
        phase_good,
        atol=1e-12,
    )
    pm_candidates = 180.0 + np.degrees(pm_phase_at_wc)
    pm_wc_candidates = np.full_like(pm_log_wc, np.nan)
    pm_wc_candidates[pm_mask] = np.exp(pm_log_wc[pm_mask])
    has_wc_good, wc_good, pm_good = _select_worst_metric_batch(
        pm_candidates,
        pm_wc_candidates,
        pm_mask,
    )
    has_wc[good_idx] = has_wc_good
    wc[good_idx] = wc_good
    pm_deg[good_idx] = np.where(has_wc_good, pm_good, np.nan)

    gm_simple_mask = min_phase_good > (-3.0 * np.pi)
    if np.any(gm_simple_mask):
        simple_local_idx = np.where(gm_simple_mask)[0]
        gm_mask, gm_log_w180, gm_mag_db_at_w180 = _interpolate_crossings_batch(
            log_w,
            phase_good[simple_local_idx],
            -np.pi,
            mag_db_good[simple_local_idx],
            atol=1e-9,
        )
        gm_candidates = -gm_mag_db_at_w180
        gm_w180_candidates = np.full_like(gm_log_w180, np.nan)
        gm_w180_candidates[gm_mask] = np.exp(gm_log_w180[gm_mask])
        has_w180_simple, w180_simple, gm_simple = _select_worst_metric_batch(
            gm_candidates,
            gm_w180_candidates,
            gm_mask,
        )
        simple_global_idx = good_idx[simple_local_idx]
        has_w180[simple_global_idx] = has_w180_simple
        w180[simple_global_idx] = w180_simple
        gm_db[simple_global_idx] = np.where(has_w180_simple, gm_simple, np.inf)

    if np.any(~gm_simple_mask):
        for local_row in np.where(~gm_simple_mask)[0]:
            global_row = good_idx[local_row]
            has_w180_row, w180_row, gm_row = _compute_gain_margin_row(
                log_w,
                phase_good[local_row],
                mag_db_good[local_row],
            )
            if has_w180_row:
                has_w180[global_row] = True
                w180[global_row] = w180_row
                gm_db[global_row] = gm_row

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
    """Convenience wrapper that evaluates the plant FRF internally.

    Args:
        plant: Plant object exposing ``system(s)``.
        Kp: Proportional gains with shape ``(P,)``.
        Ti: Integral time constants with shape ``(P,)``.
        Td: Derivative time constants with shape ``(P,)``.
        Tf: Derivative filter time constants with shape ``(P,)``.
        w: Frequency grid in rad/s with shape ``(N,)``.

    Returns:
        Same metric dictionary as ``compute_loop_metrics_batch_from_frf``.
    """
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
