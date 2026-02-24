# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Module:        utils.py
# Description:   Provides utility functions for frequency- and time-domain analysis, including
#                Bode plotting, gain crossover computation, pole analysis, and settling-time
#                evaluation. Also includes helper tools for system simulation and response
#                assessment within the PID Optimizer environment.
#
# Authors:       Florin Büchi, Thomas Stähli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zürcher Hochschule für angewandte Wissenschaften (or internal use only)
# ──────────────────────────────────────────────────────────────────────────────


import math
from typing import Callable, Union

import matplotlib.pyplot as plt
import numpy as np

SystemData = Union[Callable[[np.ndarray], np.ndarray], tuple[np.ndarray, np.ndarray, np.ndarray]]


def bode_plot(
        systems: dict[str, SystemData],
        *,
        omega: np.ndarray | None = None,
        low_exp: float = -2,
        high_exp: float = 3,
        num_points: int = 400,
        grid: bool = True,
        title: str = "Bode Diagramm"
):
    """
    Plot Bode diagrams (magnitude and phase) for multiple systems.

    Each system can be either:
        - a callable accepting `s = 1j*omega` and returning frequency response, or
        - a tuple `(omega, mag, phase)` of precomputed Bode data.

    Args:
        systems (dict[str, callable or tuple[np.ndarray, np.ndarray, np.ndarray]]):
            Mapping from system label to system data.
        omega (np.ndarray or None, optional):
            Frequency vector (rad/s) used to evaluate callables.
            If None and no precomputed omega is provided, a logarithmic sweep is generated.
        low_exp (float, optional):
            Lower exponent for logarithmic sweep (10**low_exp). Default is -2.
        high_exp (float, optional):
            Upper exponent for logarithmic sweep (10**high_exp). Default is 3.
        num_points (int, optional):
            Number of frequency points for logarithmic sweep. Default is 400.
        grid (bool, optional):
            If True, displays grid lines. Default is True.
        title (str, optional):
            Plot title

    Raises:
        TypeError: If a system entry is neither callable nor a tuple of (omega, mag, phase).

    Returns:
        None
    """
    # Determine omega
    if omega is None:
        precomputed = [sys for sys in systems.values() if isinstance(sys, tuple)]
        if precomputed:
            omega = precomputed[0][0]
        else:
            omega = np.logspace(low_exp, high_exp, num_points)

    s = 1j * omega

    fig, (ax_mag, ax_phase) = plt.subplots(2, 1, figsize=(8, 6), sharex="all")
    all_mag = []
    all_phase = []

    for label, sys in systems.items():
        if callable(sys):
            y = sys(s)
            mag = 20 * np.log10(np.abs(y))
            phase = np.angle(y, deg=True)
        elif isinstance(sys, tuple) and len(sys) == 3:
            omega_sys, mag, phase = sys
            if not np.array_equal(omega_sys, omega):
                mag = np.interp(omega, omega_sys, mag)
                phase = np.interp(omega, omega_sys, phase)
        else:
            raise TypeError(f"Unsupported system type for '{label}'")

        phase = (phase + 180) % 360 - 180  # wrap phase to [-180, 180]

        ax_mag.semilogx(omega, mag, label=label)
        ax_phase.semilogx(omega, phase, label=label)

        all_mag.append(mag)
        all_phase.append(phase)

    all_mag = np.hstack(all_mag)

    # Autoscale magnitude axis
    mag_min = np.floor(all_mag.min() / 20) * 20
    mag_max = np.ceil(all_mag.max() / 20) * 20 + 20
    ax_mag.set_ylim(mag_min, mag_max)
    ax_mag.set_yticks(np.arange(mag_min, mag_max + 1, 20))
    ax_mag.set_ylabel("Magnitude / dB")

    # Phase
    ax_phase.set_ylim(-180, 180)
    ax_phase.set_yticks(np.arange(-180, 180 + 1, 45))
    ax_phase.set_ylabel("Phase / °")
    ax_phase.set_xlabel("Frequency / rad/s")

    plt.xlim(omega.min(), omega.max())

    fig.suptitle(title, fontsize=14, fontweight='bold')

    if grid:
        ax_mag.grid(True, which="both")
        ax_phase.grid(True, which="both")

    ax_mag.legend()
    plt.tight_layout()

    return fig


def crossover_frequency(L, omega=None, tol_db=1e-3):
    """
    Compute the *outermost* gain crossover frequency (Durchtrittsfrequenz) of the loop transfer function.

    The gain crossover frequency is defined as the frequency `wc` where the loop gain satisfies:
        |L(j*wc)| = 1     <=>     20*log10(|L(j*wc)|) = 0 dB

    This implementation is robust to:
        - 0 dB plateaus (regions where the magnitude stays near 0 dB),
        - multiple crossover points (selects the outermost / highest frequency),
        - numerical fluctuations (tolerance band around 0 dB).

    Args:
        L (callable):
            Loop transfer function L(s) = C(s) * G(s), accepting complex frequency input.
            Must support vectorized evaluation: L(1j * omega) -> np.ndarray.
        omega (np.ndarray, optional):
            Frequency vector in rad/s. If None, a default logarithmic sweep from 10^-3 to 10^4
            with 4000 points is generated.
        tol_db (float, optional):
            Magnitude tolerance around 0 dB to identify a gain crossover (default: 1e-3 dB).

    Returns:
        float or None:
            The *outermost* (highest) gain crossover frequency `wc` in rad/s, or
            None if no crossover point exists.

    Notes:
        - The function interpolates in logarithmic frequency space for accuracy.
        - If the magnitude never reaches 0 dB (e.g., always below), the function returns None.
        - If the curve touches 0 dB and then falls, the edge point is used directly.

    Example:
        >>> L = lambda s: pid.controller(s) * system.system(s)
        >>> wc = crossover_frequency(L)
        >>> print(f"wc = {wc:.3f} rad/s")
    """
    if omega is None:
        omega = np.logspace(-3, 4, 4000)

    w = 1j * omega
    mag_db = 20 * np.log10(np.abs(L(w)))

    n = len(omega)
    nonneg = np.where(mag_db >= -tol_db)[0]

    if len(nonneg) == 0 or nonneg[-1] == n - 1:
        return None

    k = nonneg[-1]

    m1, m2 = mag_db[k], mag_db[k + 1]
    w1, w2 = omega[k], omega[k + 1]

    if abs(m1) <= tol_db and m2 < -tol_db:
        return w1

    logw1, logw2 = np.log10(w1), np.log10(w2)
    alpha = (0.0 - m1) / (m2 - m1)
    logwc = logw1 + alpha * (logw2 - logw1)
    wc = 10 ** logwc
    return wc


def smallest_root_realpart(denominator):
    """
    Compute the smallest real part among the poles of a linear time-invariant (LTI) system.

    The poles are obtained by computing the roots of the denominator polynomial:
        denominator[0] * s^(n) + denominator[1] * s^(n-1) + ... + denominator[n]

    The returned value corresponds to the pole lying farthest to the left
    in the complex plane, i.e., the most negative real part.

    Args:
        denominator (array_like):
            Polynomial coefficients in descending powers of `s`.
            Example: [1, 4, 6, 4, 1] represents:
                s^4 + 4*s^3 + 6*s^2 + 4*s + 1

    Returns:
        float:
            The most negative real part among all poles.

    Notes:
        - Uses numpy.roots to compute poles.
        - If multiple poles share the same real part, this function still returns
          that real value (no further disambiguation needed since only the scalar
          real part is desired).

    Example:
        >>> den = [1, 4, 6, 4, 1]
        >>> r = smallest_root_realpart(den)
        >>> print(r)
    """
    roots = np.roots(denominator)
    return np.min(roots.real)


def settling_time(
        t: np.ndarray,
        y: np.ndarray,
        r: Callable[[np.ndarray], np.ndarray],
        tolerance: float = 0.02,
        max_allowed_time: float = 60.0
) -> int:
    """Compute the strict settling time of a system response.

    The strict settling time is defined as the earliest time after which the
    output trajectory remains permanently within the tolerance band around the
    reference trajectory ``r(t)``. The reference ``r`` must be a callable that
    takes the time vector and returns a reference trajectory of equal length.

    Temporary excursions before the settling point are allowed. If the output
    never reaches a region where it stays within the tolerance band for the
    remainder of the simulation, ``max_allowed_time`` is returned.

    Args:
        t (np.ndarray):
            Time vector.
        y (np.ndarray):
            System output trajectory.
        r (Callable):
            Reference function. Must be callable as ``r(t)`` and return a
            vector of same shape as ``t``.
        tolerance (float, optional):
            Relative tolerance band (e.g. 0.02 for ±2%). Defaults to 0.02.
        max_allowed_time (float, optional):
            Upper limit for returned settling time. Defaults to 60.0.

    Returns:
        int:
            Settling time (rounded up and extended by 2 seconds), limited by
            ``max_allowed_time``.
    """
    # Evaluate reference function
    r_signal = r(t)

    # Compute tolerance band
    lower = r_signal * (1 - tolerance)
    upper = r_signal * (1 + tolerance)

    # In-band mask (True if inside tolerance)
    in_band = (y >= lower) & (y <= upper)

    # If the trajectory never enters the band, no settling possible
    if not np.any(in_band):
        return int(max_allowed_time)

    # Identify all indices where the signal is out of the tolerance band
    out_indices = np.where(~in_band)[0]

    if len(out_indices) == 0:
        # Always in-band, settled from the beginning
        t_set = t[0]
    else:
        # Latest time when the signal was out of the band
        last_out = out_indices[-1]

        # If the last out-of-band index is the final sample, no settling possible
        if last_out == len(t) - 1:
            return int(max_allowed_time)

        # Settling begins at the next sample after the last excursion
        t_set = t[last_out + 1]

    # Apply rounding + 2 seconds, enforce max limit
    t_set_adjusted = math.ceil(t_set) + 2

    if t_set_adjusted > max_allowed_time:
        return int(max_allowed_time)

    return int(t_set_adjusted)
