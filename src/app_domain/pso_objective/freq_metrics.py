from __future__ import annotations

import numpy as np
from typing import Callable

type Plant_Tf = Callable[[np.ndarray | complex], np.ndarray | complex]

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def linear_magnitude_to_db(value: float | np.ndarray) -> np.ndarray:
    """Convert linear magnitude values to decibels (dB).

    This function applies a numerical guard to avoid taking the logarithm of
    zero by clamping the magnitude to a minimum of 1e-300.

    Args:
        value: Linear magnitude value or array of values.

    Returns:
        A NumPy array containing the magnitude values converted to dB.
    """

    return 20.0 * np.log10(np.maximum(np.asarray(value, dtype=np.float64), 1e-300))


def _finite_complex_mask(z: np.ndarray) -> np.ndarray:
    return np.isfinite(z.real) & np.isfinite(z.imag)


def _ensure_frequency_grid(w: np.ndarray | tuple | list) -> np.ndarray:
    """Normalize a frequency grid specification.

    The input may be either:
    - a 1D array of frequencies, or
    - a tuple/list of the form (low_exp, high_exp, num_points), which is
      interpreted as a logspace definition.

    Args:
        w: Frequency grid specification.

    Returns:
        A 1D NumPy array of frequencies in rad/s.

    Raises:
        ValueError: If the input format is invalid.
    """

    if isinstance(w, np.ndarray) or np.isscalar(w):
        return np.asarray(w, dtype=np.float64).reshape(-1)
    if isinstance(w, (tuple, list)) and len(w) == 3:
        low, high, num = w
        return np.logspace(low, high, int(num), dtype=np.float64)
    raise ValueError("w must be array-like or (low_exp, high_exp, num_points)")


# ---------------------------------------------------------------------------
# Crossing helpers
# ---------------------------------------------------------------------------
def _find_crossings_1d(
    x: np.ndarray,
    y: np.ndarray,
    target: float,
    *,
    atol: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, float).reshape(-1)
    y = np.asarray(y, float).reshape(-1)

    if x.size < 2:
        return np.empty(0), np.empty(0, int)

    y0 = y[:-1]
    y1 = y[1:]

    hit0 = np.isclose(y0, target, atol=atol, rtol=0)
    hit1 = np.isclose(y1, target, atol=atol, rtol=0)
    sign_change = (y0 - target) * (y1 - target) < 0

    cand = hit0 | hit1 | sign_change
    if not np.any(cand):
        return np.empty(0), np.empty(0, int)

    k = np.flatnonzero(cand)
    x0 = x[k]
    x1 = x[k + 1]
    y0 = y[k]
    y1 = y[k + 1]

    flat = y0 == y1
    x_cross = np.empty_like(x0)
    x_cross[flat] = 0.5 * (x0[flat] + x1[flat])
    nf = ~flat
    x_cross[nf] = x0[nf] + (target - y0[nf]) * (x1[nf] - x0[nf]) / (y1[nf] - y0[nf])

    x_cross = np.where(hit1[k], x1, np.where(hit0[k], x0, x_cross))

    if x_cross.size > 1:
        keep = np.ones_like(x_cross, bool)
        keep[1:] = x_cross[1:] != x_cross[:-1]
        x_cross = x_cross[keep]
        k = k[keep]

    return x_cross, k

def _interpolate_values_at_crossings(
    x: np.ndarray,
    y: np.ndarray,
    k_left: np.ndarray,
    x_cross: np.ndarray,
) -> np.ndarray:

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
    x = np.asarray(x, float).reshape(-1)
    y = np.asarray(y, float)
    z = np.asarray(z, float)

    y0 = y[:, :-1]
    y1 = y[:, 1:]
    z0 = z[:, :-1]
    z1 = z[:, 1:]

    x0 = x[:-1]
    x1 = x[1:]

    hit0 = np.isclose(y0, target, atol=atol, rtol=0)
    hit1 = np.isclose(y1, target, atol=atol, rtol=0)
    sign_change = (y0 - target) * (y1 - target) < 0

    cand = hit0 | hit1 | sign_change

    x0b = np.broadcast_to(x0, y0.shape)
    x1b = np.broadcast_to(x1, y0.shape)

    flat = y0 == y1
    x_cross = np.empty_like(y0)
    x_cross[flat] = 0.5 * (x0b[flat] + x1b[flat])
    nf = ~flat
    x_cross[nf] = (
            x0b[nf]
            + (target - y0[nf]) * (x1b[nf] - x0b[nf]) / (y1[nf] - y0[nf])
    )
    x_cross = np.where(hit1, x1b, np.where(hit0, x0b, x_cross))

    z_cross = np.empty_like(z0)
    same_x = x1b == x0b
    z_cross[same_x] = 0.5 * (z0[same_x] + z1[same_x])
    dx = ~same_x
    z_cross[dx] = (
            z0[dx]
            + (x_cross[dx] - x0b[dx]) * (z1[dx] - z0[dx]) / (x1b[dx] - x0b[dx])
    )
    z_cross = np.where(hit1, z1, np.where(hit0, z0, z_cross))

    return cand, x_cross, z_cross


def _select_worst_metric_batch(
        metric: np.ndarray,
    x_candidates: np.ndarray,
    candidate_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    masked = np.where(candidate_mask, metric, np.inf)
    idx = np.argmin(masked, axis=1)
    rows = np.arange(masked.shape[0])
    found = np.any(candidate_mask, axis=1)
    best_metric = np.where(found, masked[rows, idx], np.inf)
    best_x = np.where(found, x_candidates[rows, idx], np.nan)
    return found, best_x, best_metric


def _compute_gain_margin_row(
    log_w: np.ndarray,
    phase_row: np.ndarray,
    mag_db_row: np.ndarray,
) -> tuple[bool, float, float]:

    min_phase = float(np.min(phase_row))
    max_phase = float(np.max(phase_row))

    best = np.inf
    best_w = np.nan
    found = False

    target = -np.pi
    while target >= min_phase - 1e-9:
        if target <= max_phase + 1e-9:
            xs, ks = _find_crossings_1d(log_w, phase_row, target, atol=1e-9)
            if xs.size:
                mags = _interpolate_values_at_crossings(log_w, mag_db_row, ks, xs)
                gm = -mags
                i = int(np.argmin(gm))
                if gm[i] < best:
                    best = gm[i]
                    best_w = float(np.exp(xs[i]))
                    found = True
        target -= 2 * np.pi

    if not found:
        return False, np.nan, np.inf
    return True, best_w, best


# ---------------------------------------------------------------------------
# Core metric engine
# ---------------------------------------------------------------------------

def compute_loop_metrics_batch_from_open_loop(
        L: np.ndarray,
    w: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute classical loop stability metrics from open-loop FRFs.

    This function evaluates:
    - phase margin (PM)
    - gain margin (GM)
    - maximum sensitivity (Ms)
    - crossover frequencies (wc, w180)

    The input open-loop transfer function L(jw) may represent a batch of
    candidates, enabling vectorized evaluation.

    Args:
        L: Open-loop frequency response(s) with shape (P, N) or (N,).
        w: Frequency grid of shape (N,).

    Returns:
        A dictionary containing:
            pm_deg: Phase margin in degrees.
            gm_db: Gain margin in dB.
            ms_db: Maximum sensitivity in dB.
            wc: Frequency of worst phase margin.
            w180: Frequency of worst gain margin.
            has_wc: Boolean flags for PM existence.
            has_w180: Boolean flags for GM existence.
            numerically_valid_particles: Validity mask for each candidate.

    Raises:
        ValueError: If the input dimensions are inconsistent.
    """

    w = np.asarray(w, float).reshape(-1)
    L = np.asarray(L, complex)
    if L.ndim == 1:
        L = L.reshape(1, -1)

    P, N = L.shape
    log_w = np.log(w)

    S = 1 / (1 + L)

    valid = np.all(_finite_complex_mask(L), axis=1) & np.all(_finite_complex_mask(S), axis=1)
    good = np.where(valid)[0]

    pm = np.full(P, np.nan)
    gm = np.full(P, np.inf)
    ms = np.full(P, np.inf)
    wc = np.full(P, np.nan)
    w180 = np.full(P, np.nan)
    has_wc = np.zeros(P, bool)
    has_w180 = np.zeros(P, bool)

    if good.size == 0:
        return dict(
            pm_deg=pm,
            gm_db=gm,
            ms_db=ms,
            has_wc=has_wc,
            has_w180=has_w180,
            w180=w180,
            numerically_valid_particles=valid
        )

    Lg = L[good]
    Sg = S[good]

    ms_good = linear_magnitude_to_db(np.max(np.abs(Sg), axis=1))
    ms[good] = ms_good

    mag_db = linear_magnitude_to_db(np.abs(Lg))
    phase = np.unwrap(np.angle(Lg), axis=1)
    min_phase = np.min(phase, axis=1)

    # Phase margin
    pm_mask, pm_log_wc, pm_phase = _interpolate_crossings_batch(
        log_w, mag_db, 0.0, phase, atol=1e-12
    )
    pm_candidates = 180 + np.degrees(pm_phase)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        wc_candidates = np.where(pm_mask, np.exp(pm_log_wc), np.nan)

    found_wc, wc_good, pm_good = _select_worst_metric_batch(
        pm_candidates, wc_candidates, pm_mask
    )
    has_wc[good] = found_wc
    wc[good] = wc_good
    pm[good] = np.where(found_wc, pm_good, np.nan)

    # Gain margin
    simple = min_phase > -3 * np.pi
    if np.any(simple):
        idx = np.where(simple)[0]
        gm_mask, gm_log_w, gm_mag = _interpolate_crossings_batch(
            log_w, phase[idx], -np.pi, mag_db[idx], atol=1e-9
        )
        gm_candidates = -gm_mag

        with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
            w180_candidates = np.where(gm_mask, np.exp(gm_log_w), np.nan)

        found_gm, w180_good, gm_good = _select_worst_metric_batch(
            gm_candidates, w180_candidates, gm_mask
        )
        global_idx = good[idx]
        has_w180[global_idx] = found_gm
        w180[global_idx] = w180_good
        gm[global_idx] = np.where(found_gm, gm_good, np.inf)

    # Fallback for deep phase
    deep = np.where(~simple)[0]
    for local in deep:
        global_row = good[local]
        ok, w180_row, gm_row = _compute_gain_margin_row(
            log_w, phase[local], mag_db[local]
        )
        if ok:
            has_w180[global_row] = True
            w180[global_row] = w180_row
            gm[global_row] = gm_row

    return dict(
        pm_deg=pm,
        gm_db=gm,
        ms_db=ms,
        has_wc=has_wc,
        has_w180=has_w180,
        wc=wc,
        w180=w180,
        numerically_valid_particles=valid,
    )


# ---------------------------------------------------------------------------
# Controller-agnostic batch interface (PSO-ready)
# ---------------------------------------------------------------------------

def compute_loop_metrics_batch(
        plant_tf: Plant_Tf,
        controller_tf: Callable[[Plant_Tf, np.ndarray, np.ndarray], np.ndarray],
        X: np.ndarray,
        w: np.ndarray | tuple | list,
) -> dict[str, np.ndarray]:
    """Compute loop stability metrics for a batch of controller candidates.

    This function evaluates a batch of controllers that share the same
    structure but differ in parameter values. The controller class must
    implement a vectorized batch FRF method:

        @classmethod
        def frf_batch(cls, X, s) -> np.ndarray

    Args:
        plant_tf: Function to compute the tf of a plant
        controller_tf: Function to compute the tf of a controller.
        X: Parameter matrix of shape (P, n_params), where each row contains
           one controller candidate.
        w: Frequency grid, either as a 1D array or a logspace tuple/list.

    Returns:
        A dictionary of loop stability metrics, as produced by
        compute_loop_metrics_batch_from_open_loop().

    Raises:
        ValueError: If the controller class does not implement frf_batch().
    """
    w_arr = _ensure_frequency_grid(w)
    s = 1j * w_arr

    L = controller_tf(plant_tf, X, s)

    return compute_loop_metrics_batch_from_open_loop(L, w_arr)
