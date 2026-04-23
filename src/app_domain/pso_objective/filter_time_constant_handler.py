import math
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class TfLimitReport:
    """Report for the desired raw D-filter time constant and the applied limit.

    Attributes:
        tf_raw: Desired unbounded filter time constant computed from ``Td / N``.
        tf_effective: Filter time constant actually used after applying limits.
        tf_min: Active lower bound on the filter time constant.
        simulation_limit: Lower bound imposed by the simulation step size.
        sampling_limit: Lower bound imposed by the real sampling rate.
        limited: Whether any lower-limit clamp was applied.
        limited_by_simulation: Whether the simulation-step limit was active.
        limited_by_sampling: Whether the sampling-rate limit was active.
        min_sampling_rate_hz: Sampling rate required to realize the effective
            filter time constant ``tf_effective``.
    """
    tf_raw: float
    tf_effective: float
    tf_min: float
    simulation_limit: float
    sampling_limit: float
    limited: bool
    limited_by_simulation: bool
    limited_by_sampling: bool
    # Sampling-rate suggestion for realizing the effective target Tf.
    min_sampling_rate_hz: float


def normalize_positive_scalar(value: float, name: str) -> float:
    normalized = float(value)
    if normalized <= 0.0:
        raise ValueError(f"{name} must be > 0.")
    return normalized


def normalize_sampling_rate_hz(sampling_rate_hz: float | None) -> float | None:
    if sampling_rate_hz is None:
        return None
    return normalize_positive_scalar(sampling_rate_hz, "sampling_rate_hz")


def compute_effective_tf_report(
        Td: float,
        dt: float,
        *,
        tf_tuning_factor_n: float = 5.0,
        tf_limit_factor_k: float = 5.0,
        sampling_rate_hz: float | None = None,
) -> TfLimitReport:
    """Compute raw and limited derivative-filter time constants for one ``Td``.

    Args:
        Td: Derivative time constant candidate.
        dt: Simulation time step.
        tf_tuning_factor_n: D-filter tuning factor ``N`` in ``Tf = Td / N``.
        tf_limit_factor_k: Lower-limit factor ``k`` in
            ``Tf >= k * max(dt, Ts_real)``.
        sampling_rate_hz: Optional real-system sampling rate in Hz.

    Returns:
        TfLimitReport: Report containing the desired raw filter time constant,
        the applied effective value, active limits, and the sampling-rate
        recommendation needed to realize ``tf_effective``.
    """
    td = float(Td)
    sim_dt = normalize_positive_scalar(dt, "dt")
    n_factor = normalize_positive_scalar(tf_tuning_factor_n, "tf_tuning_factor_n")
    k_factor = normalize_positive_scalar(tf_limit_factor_k, "tf_limit_factor_k")
    rate_hz = normalize_sampling_rate_hz(sampling_rate_hz)

    if td <= 0.0:
        return TfLimitReport(
            tf_raw=0.0,
            tf_effective=0.0,
            tf_min=0.0,
            simulation_limit=0.0,
            sampling_limit=0.0,
            limited=False,
            limited_by_simulation=False,
            limited_by_sampling=False,
            min_sampling_rate_hz=np.nan,
        )

    tf_raw = td / n_factor
    simulation_limit = k_factor * sim_dt
    sampling_limit = 0.0 if rate_hz is None else (k_factor / rate_hz)
    tf_min = max(simulation_limit, sampling_limit)
    tf_effective = max(tf_raw, tf_min)

    limited_by_simulation = (
            tf_raw < simulation_limit
            and math.isclose(tf_effective, simulation_limit, rel_tol=1e-12, abs_tol=1e-12)
    )
    limited_by_sampling = (
            rate_hz is not None
            and tf_raw < sampling_limit
            and math.isclose(tf_effective, sampling_limit, rel_tol=1e-12, abs_tol=1e-12)
    )
    limited = limited_by_simulation or limited_by_sampling
    # Sampling-rate recommendation for realizing the actually applied filter
    # time constant.
    min_sampling_rate_hz = k_factor / tf_effective

    return TfLimitReport(
        tf_raw=tf_raw,
        tf_effective=tf_effective,
        tf_min=tf_min,
        simulation_limit=simulation_limit,
        sampling_limit=sampling_limit,
        limited=limited,
        limited_by_simulation=limited_by_simulation,
        limited_by_sampling=limited_by_sampling,
        min_sampling_rate_hz=min_sampling_rate_hz,
    )


def compute_effective_tf_batch(
        Td: np.ndarray,
        dt: float,
        *,
        tf_tuning_factor_n: float = 5.0,
        tf_limit_factor_k: float = 5.0,
        sampling_rate_hz: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    sim_dt = normalize_positive_scalar(dt, "dt")
    n_factor = normalize_positive_scalar(tf_tuning_factor_n, "tf_tuning_factor_n")
    k_factor = normalize_positive_scalar(tf_limit_factor_k, "tf_limit_factor_k")
    rate_hz = normalize_sampling_rate_hz(sampling_rate_hz)

    td = np.asarray(Td, dtype=np.float64)
    tf_raw = np.zeros_like(td, dtype=np.float64)
    tf_effective = np.zeros_like(td, dtype=np.float64)

    active = td > 0.0
    if np.any(active):
        tf_raw[active] = td[active] / n_factor
        tf_min = max(k_factor * sim_dt, 0.0 if rate_hz is None else (k_factor / rate_hz))
        tf_effective[active] = np.maximum(tf_raw[active], tf_min)

    return tf_raw, tf_effective
