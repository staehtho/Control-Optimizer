# ------------------------------------------------------------------------------
# Project:       PID Optimizer
# Module:        pso_system_optimization.py
# Description:   Provides Numba-accelerated simulation routines and performance index evaluation
#                for PSO-based PID optimization. Includes PID update logic, ODE solvers,
#                closed-loop and open-loop response functions, and a vectorized PSO objective
#                function for evaluating multiple PID parameter sets in parallel.
#
# Authors:       Florin Buechi, Thomas Staehli
# Created:       01.12.2025
# Modified:      09.03.2026
# Version:       1.2
#
# License:       ZHAW Zuercher Hochschule fuer angewandte Wissenschaften (or internal use only)
# ------------------------------------------------------------------------------

import math
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
from numba import njit, prange, types, float64, int64

from .PIDClosedLoop import PIDClosedLoop
from .closedLoop import ClosedLoop
from .enums import *
from .freq_metrics import compute_loop_metrics_batch_from_frf


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


def _normalize_positive_scalar(value: float, name: str) -> float:
    normalized = float(value)
    if normalized <= 0.0:
        raise ValueError(f"{name} must be > 0.")
    return normalized


def _normalize_sampling_rate_hz(sampling_rate_hz: float | None) -> float | None:
    if sampling_rate_hz is None:
        return None
    return _normalize_positive_scalar(sampling_rate_hz, "sampling_rate_hz")


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
    sim_dt = _normalize_positive_scalar(dt, "dt")
    n_factor = _normalize_positive_scalar(tf_tuning_factor_n, "tf_tuning_factor_n")
    k_factor = _normalize_positive_scalar(tf_limit_factor_k, "tf_limit_factor_k")
    rate_hz = _normalize_sampling_rate_hz(sampling_rate_hz)

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
            min_sampling_rate_hz=0.0,
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
    sim_dt = _normalize_positive_scalar(dt, "dt")
    n_factor = _normalize_positive_scalar(tf_tuning_factor_n, "tf_tuning_factor_n")
    k_factor = _normalize_positive_scalar(tf_limit_factor_k, "tf_limit_factor_k")
    rate_hz = _normalize_sampling_rate_hz(sampling_rate_hz)

    td = np.asarray(Td, dtype=np.float64)
    tf_raw = np.zeros_like(td, dtype=np.float64)
    tf_effective = np.zeros_like(td, dtype=np.float64)

    active = td > 0.0
    if np.any(active):
        tf_raw[active] = td[active] / n_factor
        tf_min = max(k_factor * sim_dt, 0.0 if rate_hz is None else (k_factor / rate_hz))
        tf_effective[active] = np.maximum(tf_raw[active], tf_min)

    return tf_raw, tf_effective


class PsoFunc:
    """
    Wrapper for Particle Swarm Optimization (PSO) of a PID controller.

    Frequency-domain constraints with feasibility-aware scalar outputs:
      - Compute PM/GM/Ms first (fast, no time simulation).
      - Compute normalized violation V.
      - If V > 0: use V as scalar cost proxy (no time simulation).
      - Else: compute time-domain performance index (e.g., ITAE).

    Important after feasibility-aware PSO selection:
      - Ranking uses (feasible, V, J), not scalar cost alone.
      - Scalar cost is interpreted as J for feasible candidates and V for infeasible candidates.

    Optional time-domain overshoot handling (step references only):
      - ``calculate_overshoot`` enables overshoot as a diagnostic metric.
      - ``use_overshoot_control`` applies the measured overshoot as an
        additional feasibility constraint.
      - Allowed overshoot is measured relative to the step height.
      - allowed_overshoot_pct = 0 means strict no-overshoot.
      - Positive and negative steps are handled with one signed formula.

    Optional time-domain maximum slew-rate handling:
      - ``calculate_max_du_dt`` enables ``max_du_dt`` as a diagnostic metric.
      - ``use_max_du_dt_constraint`` applies the measured metric as an
        additional feasibility constraint.
      - The metric is measured on the saturated actuator signal ``u_sat``.
      - ``max_du_dt`` is the maximum absolute control-rate estimate over a
        sliding window of ``m`` simulation steps:
        ``max(|u[k] - u[k-m]| / (m * dt))``.
      - The window length ``m`` is configured via ``du_dt_window_steps``.
      - A larger window smooths short-lived spikes but also makes the metric
        less sensitive to very fast oscillations.

    Constraints (policies):
      - PM is minimum only: PM >= PM_min_deg
        If PM missing (has_wc=False) => infeasible.
      - GM is minimum only: GM_dB >= GM_min_db
        If GM missing => GM=+inf => OK (violation 0).
      - Ms is maximum in dB: Ms <= Ms_max_db
      - Non-finite frequency responses are treated as infeasible (guarded by freq_metrics).

    NOTE (02.03.2026):
      - Adaptive 2-pass frequency sweep removed.
      - Single configurable frequency grid is always used.
    """

    def __init__(
        self,
        controller: ClosedLoop,
        t0: float,
        t1: float,
        dt: float,
        r: Callable[[np.ndarray], np.ndarray] | None = None,
        l: Callable[[np.ndarray], np.ndarray] | None = None,
        n: Callable[[np.ndarray], np.ndarray] | None = None,
        solver: MySolver = MySolver.RK4,
        performance_index: PerformanceIndex = PerformanceIndex.ITAE,
        swarm_size: int = 40,
        pre_compiling: bool = True,
        *,
        use_freq_metrics: bool = True,
        tf_tuning_factor_n: float = 5.0,
        tf_limit_factor_k: float = 5.0,
        sampling_rate_hz: float | None = None,
        # Frequency grid
        freq_low_exp: float = -5.0,
        freq_high_exp: float = 5.0,
        freq_points: int = 450,
        # Constraints
        pm_min_deg: float = 60.0,
        gm_min_db: float = 5.0,
        ms_max_db: float | None = 20.0 * math.log10(2.0),
        use_overshoot_control: bool = False,
        allowed_overshoot_pct: float = 0.0,
            calculate_overshoot: bool = False,
            use_max_du_dt_constraint: bool = False,
            calculate_max_du_dt: bool = False,
            allowed_max_du_dt: float = 0.0,
            du_dt_window_steps: int = 10,
        log_path: str | None = None, # TODO FLO rueckgaengig logging
        enable_logging: bool = False, # TODO FLO rueckgaengig logging
    ) -> None:
        """
        Initialize a PsoFunc instance.

        Args:
            controller: PID controller instance to be optimized.
                Anti-windup configuration, including ``ka`` for
                ``BACKCALCULATION``, is taken from this controller.
            t0: Simulation start time.
            t1: Simulation end time.
            dt: Simulation time step.
            r: Reference (setpoint) function. If None, zeros.
            l: Disturbance at plant input (Z1). If None, zeros.
            n: Disturbance at measurement/output (Z2). If None, zeros.
            solver: ODE solver selection (default RK4).
            performance_index: IAE/ISE/ITAE/ITSE.
            swarm_size: Number of particles used by PSO (for warm-up).
            pre_compiling: If True, run one warm-up call to pre-compile Numba functions.

            freq_low_exp, freq_high_exp, freq_points:
                Frequency grid definition w = logspace(freq_low_exp, freq_high_exp, freq_points).

            use_freq_metrics:
                If True, evaluate PM/GM/Ms first and derive feasibility from frequency metrics.
                If False, all candidates are treated as frequency-feasible.
            tf_tuning_factor_n:
                D-filter tuning factor ``N`` in ``Tf = Td / N``.
            tf_limit_factor_k:
                Lower-limit factor ``k`` used in ``Tf >= k * max(dt, Ts_real)``.
            sampling_rate_hz:
                Optional real-system sampling rate in Hz. If omitted, only the simulation
                time step ``dt`` limits ``Tf``.
            pm_min_deg: Phase margin minimum in degrees (PM >= pm_min_deg). PM missing => infeasible.
            gm_min_db: Gain margin minimum in dB (GM >= gm_min_db). GM missing => treated as +inf => OK.
            ms_max_db: Sensitivity peak maximum in dB (Ms <= ms_max_db). If None, the Ms
                constraint is disabled.
            use_overshoot_control:
                If True, overshoot becomes an additional feasibility criterion after time simulation.
            allowed_overshoot_pct:
                Maximum allowed overshoot in percent before a feasible time response is marked infeasible.
            calculate_overshoot:
                If True, compute ``overshoot_pct`` as a diagnostic metric even when
                ``use_overshoot_control`` is False. The metric is only defined for
                step-like references; other inputs leave ``overshoot_pct`` as NaN.
            use_max_du_dt_constraint:
                If True, ``max_du_dt`` becomes an additional feasibility
                criterion after time simulation.
            calculate_max_du_dt:
                If True, compute ``max_du_dt`` as a diagnostic metric even when
                ``use_max_du_dt_constraint`` is False. When both flags are
                disabled, ``max_du_dt`` remains NaN and the metric is skipped.
            allowed_max_du_dt:
                Maximum allowed absolute control-rate value before a feasible
                time response is marked infeasible.
            du_dt_window_steps:
                Sliding-window length ``m`` used for the finite-difference
                estimate ``|u[k] - u[k-m]| / (m * dt)``.
            log_path:
                Optional CSV path used by the temporary logging pipeline.
            enable_logging:
                Enables temporary per-call CSV logging when True.

            cost is interpreted as:
              - J for feasible candidates
              - V for infeasible candidates
        """
        self.controller = controller

        self.t0 = t0
        self.t1 = t1
        self.dt = dt
        self.t_eval = np.arange(t0, t1 + dt, dt)
        self.tf_tuning_factor_n = _normalize_positive_scalar(tf_tuning_factor_n, "tf_tuning_factor_n")
        self.tf_limit_factor_k = _normalize_positive_scalar(tf_limit_factor_k, "tf_limit_factor_k")
        self.sampling_rate_hz = _normalize_sampling_rate_hz(sampling_rate_hz)

        # TODO FLO rueckgaengig logging
        self.enable_logging = bool(enable_logging)
        self.log_path = log_path
        self._run_id = 0  # PSO-Durchlauf (aeussere Schleife)
        self._call_id = 0  # zaehlt __call__-Aufrufe
        self._wrote_header = False  # CSV header nur 1x
        self._last_eval: dict[str, np.ndarray] | None = None
        self._pending_log_batch: dict[str, np.ndarray] | None = None

        # Toggle frequency-domain metrics/constraints
        self.use_freq_metrics = bool(use_freq_metrics)

        if self.use_freq_metrics:
            self._freq_low_exp = float(freq_low_exp)
            self._freq_high_exp = float(freq_high_exp)
            self._freq_points = int(freq_points)

            self._w = np.logspace(self._freq_low_exp, self._freq_high_exp, self._freq_points).astype(np.float64)
            self._s = 1j * self._w
            self._G = np.asarray(self.controller.plant.system(self._s), dtype=np.complex128)

        self._pre_compiling = pre_compiling

        if r is None:
            r = lambda t: np.zeros_like(t)
        if l is None:
            l = lambda t: np.zeros_like(t)
        if n is None:
            n = lambda t: np.zeros_like(t)

        self.r_eval = r(self.t_eval)
        self.l_eval = l(self.t_eval)
        self.n_eval = n(self.t_eval)

        # Extract state-space matrices and ensure they are contiguous for Numba
        A, B, C, D = self.controller.plant.get_ABCD()
        self.A = np.ascontiguousarray(A, dtype=np.float64)

        # SISO -> (n,)
        self.B = np.ascontiguousarray(B.flatten(), dtype=np.float64)
        self.C = np.ascontiguousarray(C.flatten(), dtype=np.float64)
        self.D = float(D[0, 0])

        self.plant_order = self.controller.plant.get_plant_order()

        self.performance_index = map_enum_to_int(performance_index)
        self.control_constraint = np.array(self.controller.control_constraint, dtype=np.float64)
        self.anti_windup_method = map_enum_to_int(self.controller.anti_windup_method)
        self.ka = float(self.controller.ka)
        self.solver = map_enum_to_int(solver)

        self.swarm_size = swarm_size

        # --- constraint parameters (dynamic from outside) ---
        self.pm_min_deg = float(pm_min_deg)
        self.gm_min_db = float(gm_min_db)
        self.ms_max_db = None if ms_max_db is None else float(ms_max_db)
        self.use_overshoot_control = bool(use_overshoot_control)
        self.allowed_overshoot_pct = float(allowed_overshoot_pct)
        self.calculate_overshoot = bool(calculate_overshoot)
        self._overshoot_step_amplitude_abs = 0.0
        self._overshoot_step_start_idx = 0
        self._overshoot_step_sign = 0.0
        self._overshoot_r_final = 0.0
        self.use_max_du_dt_constraint = bool(use_max_du_dt_constraint)
        self.calculate_max_du_dt = bool(calculate_max_du_dt)
        self.allowed_max_du_dt = float(allowed_max_du_dt)
        self.du_dt_window_steps = int(du_dt_window_steps)
        self._update_max_du_dt_cache()
        self._update_overshoot_control_cache()

        # Pre-compile Numba functions
        if self._pre_compiling:
            start = time.time()
            X = np.array([[10.0, 9.6, 0.3] for _ in range(swarm_size)], dtype=np.float64)
            _ = self.__call__(X)
            end = time.time()
            print(f"Pre-compiling: {end - start:0.6f} sec", flush=True)
            time.sleep(0.05)
            self._pre_compiling = False

    def evaluate_tf_for_td(self, Td: float) -> TfLimitReport:
        return compute_effective_tf_report(
            Td=Td,
            dt=self.dt,
            tf_tuning_factor_n=self.tf_tuning_factor_n,
            tf_limit_factor_k=self.tf_limit_factor_k,
            sampling_rate_hz=self.sampling_rate_hz,
        )

    # TODO FLO rueckgaengig logging
    def set_run_id(self, run_id: int) -> None:
        self._run_id = int(run_id)

    # TODO FLO rueckgaengig logging
    def _ensure_log_header(self) -> None:
        if (not self.enable_logging) or (not self.log_path) or self._wrote_header:
            return

        import os
        header = (
            "run_id,call_id,particle_idx,"
            "Kp,Ti,Td,"
            "pm_deg,gm_db,ms_db,wc,w180,"
            "V,V_freq,V_ov,V_du,V_total,feasible_final,time_simulated,overshoot_pct,"
            "max_du_dt,"
            "time_cost,perf_J,total_cost,objective_cost,"
            "pbest_updated,gbest_updated,"
            "pbest_feasible,pbest_violation,pbest_perf,pbest_cost,"
            "gbest_feasible,gbest_violation,gbest_perf,gbest_cost\n"
        )

        # Header nur schreiben, wenn Datei neu/leer ist
        need_header = (not os.path.exists(self.log_path)) or (os.path.getsize(self.log_path) == 0)
        if need_header:
            with open(self.log_path, "a", encoding="utf-8", newline="") as f:
                f.write(header)

        self._wrote_header = True

    # TODO FLO rueckgaengig logging
    def _log_batch(
            self,
            Kp: np.ndarray, Ti: np.ndarray, Td: np.ndarray,
            pm: np.ndarray, gm: np.ndarray, ms_db: np.ndarray,
            wc: np.ndarray, w180: np.ndarray,
            V: np.ndarray,
            V_freq: np.ndarray,
            V_ov: np.ndarray,
            V_du: np.ndarray,
            V_total: np.ndarray,
            feasible_final: np.ndarray,
            time_sim: np.ndarray,
            overshoot_pct: np.ndarray,
            max_du_dt: np.ndarray,
            time_cost: np.ndarray,
            perf_J: np.ndarray,
            total_cost: np.ndarray,
            objective_cost: np.ndarray,
            pbest_updated: np.ndarray,
            gbest_updated: np.ndarray,
            pbest_feasible: np.ndarray,
            pbest_violation: np.ndarray,
            pbest_perf: np.ndarray,
            pbest_cost: np.ndarray,
            gbest_feasible: np.ndarray,
            gbest_violation: np.ndarray,
            gbest_perf: np.ndarray,
            gbest_cost: np.ndarray,
    ) -> None:
        if (not self.enable_logging) or (not self.log_path):
            return

        self._ensure_log_header()

        # schnelles CSV: Stringbuilder (kein pandas, kein csv.writer Overhead)
        lines = []
        run_id = self._run_id
        call_id = self._call_id
        for i in range(Kp.shape[0]):
            lines.append(
                f"{run_id},{call_id},{i},"
                f"{Kp[i]},{Ti[i]},{Td[i]},"
                f"{pm[i]},{gm[i]},{ms_db[i]},{wc[i]},{w180[i]},"
                f"{V[i]},{V_freq[i]},{V_ov[i]},{V_du[i]},{V_total[i]},{int(feasible_final[i])},{int(time_sim[i])},{overshoot_pct[i]},"
                f"{max_du_dt[i]},"
                f"{time_cost[i]},{perf_J[i]},{total_cost[i]},{objective_cost[i]},"
                f"{int(pbest_updated[i])},{int(gbest_updated[i])},"
                f"{int(pbest_feasible[i])},{pbest_violation[i]},{pbest_perf[i]},{pbest_cost[i]},"
                f"{int(gbest_feasible[i])},{gbest_violation[i]},{gbest_perf[i]},{gbest_cost[i]}\n"
            )

        with open(self.log_path, "a", encoding="utf-8", newline="") as f:
            f.writelines(lines)

    def finalize_log_batch(
        self,
        *,
        particles: list,
        gbest,
        pbest_updated: np.ndarray,
        gbest_updated: np.ndarray,
    ) -> None:
        """Finalize deferred batch logging with PSO state (pBest/gBest)."""
        if (not self.enable_logging) or (self._pending_log_batch is None):
            return

        batch = self._pending_log_batch
        P = int(batch["Kp"].shape[0])

        pbest_feasible = np.array([bool(p.p_best_feasible) for p in particles], dtype=np.bool_)
        pbest_violation = np.array([float(p.p_best_violation) for p in particles], dtype=np.float64)
        pbest_perf = np.array([float(p.p_best_perf) for p in particles], dtype=np.float64)
        pbest_cost = np.array([float(p.p_best_cost) for p in particles], dtype=np.float64)

        gbest_feasible = np.full(P, bool(gbest.p_best_feasible), dtype=np.bool_)
        gbest_violation = np.full(P, float(gbest.p_best_violation), dtype=np.float64)
        gbest_perf = np.full(P, float(gbest.p_best_perf), dtype=np.float64)
        gbest_cost = np.full(P, float(gbest.p_best_cost), dtype=np.float64)

        self._log_batch(
            Kp=batch["Kp"],
            Ti=batch["Ti"],
            Td=batch["Td"],
            pm=batch["pm"],
            gm=batch["gm"],
            ms_db=batch["ms_db"],
            wc=batch["wc"],
            w180=batch["w180"],
            V=batch["V"],
            V_freq=batch["V_freq"],
            V_ov=batch["V_ov"],
            V_du=batch["V_du"],
            V_total=batch["V_total"],
            feasible_final=batch["feasible_final"],
            time_sim=batch["time_sim"],
            overshoot_pct=batch["overshoot_pct"],
            max_du_dt=batch["max_du_dt"],
            time_cost=batch["time_cost"],
            perf_J=batch["perf_J"],
            total_cost=batch["total_cost"],
            objective_cost=batch["objective_cost"],
            pbest_updated=np.asarray(pbest_updated, dtype=np.bool_),
            gbest_updated=np.asarray(gbest_updated, dtype=np.bool_),
            pbest_feasible=pbest_feasible,
            pbest_violation=pbest_violation,
            pbest_perf=pbest_perf,
            pbest_cost=pbest_cost,
            gbest_feasible=gbest_feasible,
            gbest_violation=gbest_violation,
            gbest_perf=gbest_perf,
            gbest_cost=gbest_cost,
        )
        self._pending_log_batch = None


    def set_constraints(
        self,
        *,
        pm_min_deg: float | None = None,
        gm_min_db: float | None = None,
        ms_max_db: float | None = None,
        use_overshoot_control: bool | None = None,
        allowed_overshoot_pct: float | None = None,
            calculate_overshoot: bool | None = None,
            use_max_du_dt_constraint: bool | None = None,
            calculate_max_du_dt: bool | None = None,
            allowed_max_du_dt: float | None = None,
            du_dt_window_steps: int | None = None,
    ) -> None:
        """Update constraints and optional diagnostic metrics dynamically."""
        if pm_min_deg is not None:
            self.pm_min_deg = float(pm_min_deg)
        if gm_min_db is not None:
            self.gm_min_db = float(gm_min_db)
        if ms_max_db is not None:
            self.ms_max_db = float(ms_max_db)
        if use_overshoot_control is not None:
            self.use_overshoot_control = bool(use_overshoot_control)
        if allowed_overshoot_pct is not None:
            self.allowed_overshoot_pct = float(allowed_overshoot_pct)
        if calculate_overshoot is not None:
            self.calculate_overshoot = bool(calculate_overshoot)
        if use_max_du_dt_constraint is not None:
            self.use_max_du_dt_constraint = bool(use_max_du_dt_constraint)
        if calculate_max_du_dt is not None:
            self.calculate_max_du_dt = bool(calculate_max_du_dt)
        if allowed_max_du_dt is not None:
            self.allowed_max_du_dt = float(allowed_max_du_dt)
        if du_dt_window_steps is not None:
            self.du_dt_window_steps = int(du_dt_window_steps)

        self._update_max_du_dt_cache()
        self._update_overshoot_control_cache()

    def _update_max_du_dt_cache(self) -> None:
        """Validate cached parameters for the ``max_du_dt`` window metric."""
        if self.du_dt_window_steps < 1:
            raise ValueError("du_dt_window_steps must be >= 1.")
        if self.use_max_du_dt_constraint and self.allowed_max_du_dt < 0.0:
            raise ValueError(
                "allowed_max_du_dt must be >= 0 when use_max_du_dt_constraint=True."
            )

    def _update_overshoot_control_cache(self) -> None:
        """Precompute overshoot helpers from the sampled reference trace.

        Overshoot is only defined for single-step references. When
        ``calculate_overshoot`` is enabled without the constraint, non-step
        references keep the cache disabled so the runtime metric returns NaN
        instead of raising. Constraint mode remains strict and still rejects
        invalid references.
        """
        eps = 1e-15
        self._overshoot_step_amplitude_abs = 0.0
        self._overshoot_step_start_idx = 0
        self._overshoot_step_sign = 0.0
        self._overshoot_r_final = float(self.r_eval[-1])

        compute_overshoot = self.calculate_overshoot or self.use_overshoot_control
        if not compute_overshoot:
            return

        if self.use_overshoot_control and self.allowed_overshoot_pct < 0.0:
            raise ValueError("allowed_overshoot_pct must be >= 0 when use_overshoot_control=True.")

        r0 = float(self.r_eval[0])
        rf = float(self.r_eval[-1])
        dr = rf - r0

        if abs(dr) > eps:
            tol = max(1e-12, 1e-9 * abs(dr))
            change_idx = np.where(~np.isclose(self.r_eval, r0, atol=tol, rtol=0.0))[0]
            if change_idx.size == 0:
                if self.use_overshoot_control:
                    raise ValueError("overshoot_control could not detect a valid step transition.")
                return

            step_start_idx = int(change_idx[0])
            if not np.all(np.isclose(self.r_eval[step_start_idx:], rf, atol=tol, rtol=0.0)):
                if self.use_overshoot_control:
                    raise ValueError("overshoot_control requires a single step reference.")
                return

            self._overshoot_step_amplitude_abs = abs(dr)
            self._overshoot_step_start_idx = step_start_idx
            self._overshoot_step_sign = float(np.sign(dr))
            self._overshoot_r_final = rf
            return

        if abs(rf) > eps:
            tol = max(1e-12, 1e-9 * abs(rf))
            if not np.all(np.isclose(self.r_eval, rf, atol=tol, rtol=0.0)):
                if self.use_overshoot_control:
                    raise ValueError("overshoot_control requires a single step reference.")
                return

            # Immediate step at t0 represented as constant non-zero level in sampled r_eval.
            self._overshoot_step_amplitude_abs = abs(rf)
            self._overshoot_step_start_idx = 0
            self._overshoot_step_sign = float(np.sign(rf))
            self._overshoot_r_final = rf
            return

        if self.use_overshoot_control:
            raise ValueError("overshoot_control requires a non-zero step amplitude.")

    def _compute_violation_batch(self, metrics: dict[str, np.ndarray]) -> np.ndarray:
        """Compute normalized constraint violation V for a batch.

        Returns:
            V: (P,) array, 0 for feasible candidates, >0 for infeasible.
        """
        pm = metrics["pm_deg"]
        gm = metrics["gm_db"]
        ms_db = metrics["ms_db"]
        has_wc = metrics["has_wc"]
        numerically_valid = metrics["numerically_valid_particles"]

        P = pm.shape[0]

        # --- hard fail mask (PM missing / non-finite / finite-guarded / Ms non-finite) ---
        hard_fail = (~numerically_valid) | (~has_wc) | (~np.isfinite(pm)) | (~np.isfinite(ms_db))

        v_pm = np.zeros(P, dtype=np.float64)
        v_gm = np.zeros(P, dtype=np.float64)
        v_ms = np.zeros(P, dtype=np.float64)

        # PM min only: PM >= PM_min_deg
        good = ~hard_fail
        if np.any(good):
            # PM constraint (disable if pm_min_deg <= 0)
            if self.pm_min_deg > 0.0:
                v_pm[good] = np.maximum(0.0, (self.pm_min_deg - pm[good]) / self.pm_min_deg)

            # GM constraint (disable if gm_min_db <= 0) ; GM=+inf => ok
            if self.gm_min_db > 0.0:
                finite_gm = np.isfinite(gm[good])
                if np.any(finite_gm):
                    idx = np.where(good)[0][finite_gm]
                    v_gm[idx] = np.maximum(0.0, (self.gm_min_db - gm[idx]) / self.gm_min_db)

            # Ms constraint in dB (disable only if ms_max_db is None)
            if self.ms_max_db is not None:
                ms_scale = max(abs(self.ms_max_db), 1.0)
                v_ms[good] = np.maximum(0.0, (ms_db[good] - self.ms_max_db) / ms_scale)

        # Hard-fails are ranked strictly worse than regular infeasible candidates.
        # We therefore force total V to +inf for hard-fail entries.
        v_pm[hard_fail] = 1.0
        v_ms[hard_fail] = 1.0

        V = v_pm + v_gm + v_ms
        V = np.nan_to_num(V, nan=np.inf, posinf=np.inf, neginf=0.0)
        V[hard_fail] = np.inf
        return V

    def evaluate_candidates(self, X: np.ndarray, defer_logging: bool = False) -> dict[str, np.ndarray]:
        """
        Evaluate candidates and expose both scalar cost and feasibility-aware data.

        Args:
            X: PID parameter matrix of shape (P, 3). Each row contains [Kp, Ti, Td].
            defer_logging:
                If True, cache batch metrics so PSO state (pBest/gBest) can be attached later
                via ``finalize_log_batch(...)``.

        Returns:
            dict with:
              - cost: scalar summary value
                (J for feasible candidates, V for infeasible candidates)
              - feasible: final feasibility flag
              - violation: total violation V
                (frequency + optional overshoot + optional max_du_dt)
              - perf: objective J (np.inf for infeasible candidates)
              - overshoot_pct: measured overshoot percentage for simulated candidates;
                NaN if overshoot evaluation is disabled or unavailable
              - max_du_dt: measured maximum absolute control-rate estimate for
                simulated candidates; NaN if evaluation is disabled or unavailable
            If defer_logging=True, core batch metrics are cached and can be finalized later
            with PSO state (pBest/gBest) via finalize_log_batch(...).
        """
        X = np.array(X, dtype=np.float64)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        if not isinstance(self.controller, PIDClosedLoop):
            raise NotImplementedError(f"Unsupported controller type: '{type(self.controller)}'")

        P = X.shape[0]

        # TODO FLO rückgängig logging
        self._call_id += 1
        self._pending_log_batch = None

        Kp = X[:, 0]
        Ti = X[:, 1]
        Td = X[:, 2]
        _, Tf = compute_effective_tf_batch(
            Td,
            dt=self.dt,
            tf_tuning_factor_n=self.tf_tuning_factor_n,
            tf_limit_factor_k=self.tf_limit_factor_k,
            sampling_rate_hz=self.sampling_rate_hz,
        )

        # --------------------------------------------------
        # 1) Optional: Frequency metrics + constraint violation
        # --------------------------------------------------
        if self.use_freq_metrics:
            with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
                metrics = compute_loop_metrics_batch_from_frf(
                    G=self._G,
                    w=self._w,
                    Kp=Kp,
                    Ti=Ti,
                    Td=Td,
                    Tf=Tf,
                )

            V = self._compute_violation_batch(metrics)
        else:
            # No frequency-domain constraints -> all candidates feasible.
            V = np.zeros(P, dtype=np.float64)
        V_freq = V.copy()
        V_ov = np.zeros(P, dtype=np.float64)
        V_du = np.zeros(P, dtype=np.float64)

        # TODO FLO rückgängig logging
        # Logging helpers (per particle)
        # --------------------------------------------------
        pm = np.full(P, np.nan, dtype=np.float64)
        gm = np.full(P, np.nan, dtype=np.float64)
        ms_db = np.full(P, np.nan, dtype=np.float64)
        wc = np.full(P, np.nan, dtype=np.float64)
        w180 = np.full(P, np.nan, dtype=np.float64)

        if self.use_freq_metrics:
            pm = metrics.get("pm_deg", pm)
            gm = metrics.get("gm_db", gm)
            ms_db = metrics.get("ms_db", ms_db)
            wc = metrics.get("wc", wc)
            w180 = metrics.get("w180", w180)

        time_sim = np.zeros(P, dtype=np.bool_)
        overshoot_pct = np.full(P, np.nan, dtype=np.float64)
        max_du_dt = np.full(P, np.nan, dtype=np.float64)
        time_cost = np.full(P, np.nan, dtype=np.float64)

        # Scalar summary value retained for logging/return compatibility.
        # Semantics:
        #   - feasible candidate   -> cost = performance J
        #   - infeasible candidate -> cost = total violation V
        # Ranking in the PSO itself uses (feasible, violation, perf), not cost alone.
        cost = np.full(P, np.nan, dtype=np.float64)
        # J for feasibility-aware ranking. Infeasible candidates keep J=inf.
        perf = np.full(P, np.inf, dtype=np.float64)

        infeasible = V > 0.0
        feasible = ~infeasible

        time_sim = feasible.copy()

        # Infeasible candidates use their total violation as scalar cost proxy.
        cost[infeasible] = V[infeasible]

        # --------------------------------------------------
        # 2) Time simulation only for currently feasible candidates
        # --------------------------------------------------
        if np.any(feasible):
            Xf = X[feasible]
            Pf = int(Xf.shape[0])
            compute_overshoot = self.calculate_overshoot or self.use_overshoot_control
            compute_max_du_dt = self.calculate_max_du_dt or self.use_max_du_dt_constraint

            perf_vals, overshoot_vals, max_du_dt_vals = _pid_pso_func(
                Xf,
                self.t_eval,
                self.dt,
                self.r_eval,
                self.l_eval,
                self.n_eval,
                self.A,
                self.B,
                self.C,
                self.D,
                self.plant_order,
                Tf[feasible],
                self.control_constraint,
                self.anti_windup_method,
                self.ka,
                self.solver,
                self.performance_index,
                1 if compute_overshoot else 0,
                self._overshoot_step_amplitude_abs,
                self._overshoot_step_start_idx,
                self._overshoot_step_sign,
                self._overshoot_r_final,
                1 if compute_max_du_dt else 0,
                self.du_dt_window_steps,
                Pf,  # IMPORTANT: swarm_size = number of feasible particles
            )
            time_cost[feasible] = perf_vals
            overshoot_pct[feasible] = overshoot_vals
            max_du_dt[feasible] = max_du_dt_vals
            perf[feasible] = perf_vals
            feasible_indices = np.where(feasible)[0]
            feasible_cost = perf_vals.copy()
            infeasible_time_constraint = np.zeros(Pf, dtype=np.bool_)

            if self.use_overshoot_control:
                overshoot_scale = max(abs(self.allowed_overshoot_pct), 1.0)
                overshoot_violation = np.maximum(
                    0.0,
                    (overshoot_vals - self.allowed_overshoot_pct) / overshoot_scale,
                )
                overshoot_violation = np.nan_to_num(overshoot_violation, nan=1.0, posinf=1.0, neginf=0.0)

                # Keep overshoot as feasibility component in total violation V.
                V_ov_local = overshoot_violation
                V_ov[feasible_indices] = V_ov_local
                V[feasible_indices] += V_ov_local
                infeasible_time_constraint |= overshoot_violation > 0.0

            if self.use_max_du_dt_constraint:
                du_dt_scale = max(abs(self.allowed_max_du_dt), 1.0)
                max_du_dt_violation = np.maximum(
                    0.0,
                    (max_du_dt_vals - self.allowed_max_du_dt) / du_dt_scale,
                )
                max_du_dt_violation = np.nan_to_num(
                    max_du_dt_violation,
                    nan=1.0,
                    posinf=1.0,
                    neginf=0.0,
                )

                V_du_local = max_du_dt_violation
                V_du[feasible_indices] = V_du_local
                V[feasible_indices] += V_du_local
                infeasible_time_constraint |= max_du_dt_violation > 0.0

            if np.any(infeasible_time_constraint):
                feasible_cost[infeasible_time_constraint] = V[feasible_indices[infeasible_time_constraint]]
                perf[feasible_indices[infeasible_time_constraint]] = np.inf
            cost[feasible] = feasible_cost

        V_total = V.copy()
        feasible_final = V_total <= 0.0

        # --------------------------------------------------
        # TODO FLO rückgängig logging
        # --------------------------------------------------
        if self.enable_logging:
            batch = {
                "Kp": Kp,
                "Ti": Ti,
                "Td": Td,
                "pm": pm,
                "gm": gm,
                "ms_db": ms_db,
                "wc": wc,
                "w180": w180,
                "V": V_total,  # backward-compatible alias
                "V_freq": V_freq,
                "V_ov": V_ov,
                "V_du": V_du,
                "V_total": V_total,
                "feasible_final": feasible_final,
                "time_sim": time_sim,
                "overshoot_pct": overshoot_pct,
                "max_du_dt": max_du_dt,
                "time_cost": time_cost,
                "perf_J": perf,
                "total_cost": cost,
                "objective_cost": cost,
            }
            if defer_logging:
                self._pending_log_batch = batch
            else:
                P_local = int(Kp.shape[0])
                false_flags = np.zeros(P_local, dtype=np.bool_)
                nan_vals = np.full(P_local, np.nan, dtype=np.float64)
                self._log_batch(
                    Kp=batch["Kp"],
                    Ti=batch["Ti"],
                    Td=batch["Td"],
                    pm=batch["pm"],
                    gm=batch["gm"],
                    ms_db=batch["ms_db"],
                    wc=batch["wc"],
                    w180=batch["w180"],
                    V=batch["V"],
                    V_freq=batch["V_freq"],
                    V_ov=batch["V_ov"],
                    V_du=batch["V_du"],
                    V_total=batch["V_total"],
                    feasible_final=batch["feasible_final"],
                    time_sim=batch["time_sim"],
                    overshoot_pct=batch["overshoot_pct"],
                    max_du_dt=batch["max_du_dt"],
                    time_cost=batch["time_cost"],
                    perf_J=batch["perf_J"],
                    total_cost=batch["total_cost"],
                    objective_cost=batch["objective_cost"],
                    pbest_updated=false_flags,
                    gbest_updated=false_flags,
                    pbest_feasible=false_flags,
                    pbest_violation=nan_vals,
                    pbest_perf=nan_vals,
                    pbest_cost=nan_vals,
                    gbest_feasible=false_flags,
                    gbest_violation=nan_vals,
                    gbest_perf=nan_vals,
                    gbest_cost=nan_vals,
                )

        result = {
            "cost": cost,
            "feasible": feasible_final,
            "violation": V_total,
            "perf": perf,
            "overshoot_pct": overshoot_pct,
            "max_du_dt": max_du_dt,
        }
        self._last_eval = result
        return result

    def __call__(self, X: np.ndarray) -> np.ndarray:
        """Backward-compatible scalar objective interface."""
        return self.evaluate_candidates(X)["cost"]

    def set_calculate_max_du_dt(self, value: bool) -> None:
        self.calculate_max_du_dt = value

        self._update_max_du_dt_cache()

    def set_calculate_overshoot(self, value: bool) -> None:
        self.calculate_overshoot = value

        self._update_overshoot_control_cache()

# =============================================================================
# Helper Functions
# =============================================================================
@njit(float64[:](float64[:, :], float64[:]), inline="always")
def _matvec_auto(A: np.ndarray, x: np.ndarray) -> np.ndarray:
    """
    Perform matrix-vector multiplication manually for Numba.

    Args:
        A: Square matrix.
        x: Vector.

    Returns:
        Result of A @ x as a 1-D numpy array.
    """
    n = A.shape[0]
    y = np.zeros(n)

    for i in range(n):
        acc = 0.0
        for j in range(n):
            acc += A[i][j] * x[j]
        y[i] = acc

    return y


@njit(float64(float64[:], float64[:]), inline="always")
def dot1D(x: np.ndarray, y: np.ndarray) -> float:
    """
    Compute dot product of two 1-D vectors manually for Numba.

    Args:
        x: Vector x.
        y: Vector y.

    Returns:
        The scalar dot product x.T @ y.
    """
    acc = 0.0
    for i in range(x.shape[0]):
        acc += x[i] * y[i]
    return acc


# =============================================================================
# PID Update
# =============================================================================
@njit(
    types.UniTuple(float64, 3)(
        float64, float64, float64, float64, float64, float64, float64, float64, float64, float64, float64, int64,
        float64
    ),
    inline="always"
)
def pid_update(e: float, e_prev: float, d_filtered_prev: float, integral_prev: float,
               Kp: float, Ti: float, Td: float, Tf: float, dt: float, u_min: float, u_max: float,
               anti_windup_method: int, ka: float) -> tuple[float, float, float]:
    """
    Perform a single PID controller update including anti-windup.

    The function computes proportional, integral and filtered derivative terms,
    applies the selected anti-windup strategy and returns the saturated control
    signal together with the updated integral and filtered derivative states.

    The application-level controller representation remains the ISA
    time-constant form ``(Kp, Ti, Td, Tf)``. Inside this numerical kernel, the
    integral and derivative contributions are evaluated through the equivalent
    local gain terms ``Ki = Kp / Ti`` and ``Kd = Kp * Td`` for efficiency.

    Args:
        e: Current control error.
        e_prev: Previous control error.
        d_filtered_prev: Previous filtered derivative state.
        integral_prev: Previous integral state.
        Kp: Proportional gain.
        Ti: Integral time constant.
        Td: Derivative time constant.
        Tf: Derivative filter time constant.
        dt: Simulation time step.
        u_min: Lower actuator limit.
        u_max: Upper actuator limit.
        anti_windup_method: Selected anti-windup method.
        ka: Scaling factor for the back-calculation feedback path.
    """
    # 1) Proportional
    P_term = Kp * e

    # 2) Integration
    if Ti > 0.0:
        integral_candidate = integral_prev + e * dt
    else:
        integral_candidate = integral_prev

    # Local gain-equivalent evaluation of the ISA controller: Ki = Kp / Ti.
    I_term_previous = Kp * (1.0 / Ti) * integral_prev if Ti > 0 else 0.0
    I_term_candidate = Kp * (1.0 / Ti) * integral_candidate if Ti > 0 else 0.0

    # 3) Derivative (filtered)
    if Td > 0.0:
        alpha = Tf / (Tf + dt)
        d_filtered_updated = alpha * d_filtered_prev + (1.0 - alpha) * ((e - e_prev) / dt)
    else:
        d_filtered_updated = 0.0

    # Local gain-equivalent evaluation of the ISA controller: Kd = Kp * Td.
    D_term = Kp * Td * d_filtered_updated

    # 4) Build u (unsat)
    u_unsat_previous = P_term + I_term_previous + D_term
    u_unsat_candidate = P_term + I_term_candidate + D_term

    # 5) Anti-windup
    if anti_windup_method == AntiWindupInt.CONDITIONAL:
        if (u_min < u_unsat_candidate < u_max) or \
                (u_unsat_candidate >= u_max and e < 0.0) or \
                (u_unsat_candidate <= u_min and e > 0.0):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_previous

    elif anti_windup_method == AntiWindupInt.CLAMPING:
        if (u_min < I_term_candidate < u_max) or \
                (I_term_candidate >= u_max and e < 0.0) or \
                (I_term_candidate <= u_min and e > 0.0):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_previous

    elif anti_windup_method == AntiWindupInt.BACKCALCULATION:
        u_sat_candidate = min(max(u_unsat_candidate, u_min), u_max)

        # The application state integrates the unscaled integral state x_I
        # with I_term = Ki * x_I and Ki = Kp / Ti. A block diagram that feeds
        # the saturation error through the scaling factor ka into the already
        # scaled I-branch therefore maps to ka * (u_sat - u_unsat) / Ki on this state.
        if Ti > 0.0 and Kp != 0.0:
            integral_updated = integral_candidate + dt * ka * (Ti / Kp) * (u_sat_candidate - u_unsat_candidate)
        else:
            integral_updated = integral_candidate

        I_term_updated = Kp * (1.0 / Ti) * integral_updated if Ti > 0.0 else 0.0
        u_unsat_updated = P_term + I_term_updated + D_term

    else:
        u_unsat_updated = 0.0
        integral_updated = 0.0

    # 6) Saturation
    u_updated = min(max(u_unsat_updated, u_min), u_max)

    return u_updated, integral_updated, d_filtered_updated


# =============================================================================
# ODE Solver
# =============================================================================
@njit(float64[:](float64[:, :], float64[:], float64[:], float64, float64), inline="always")
def rk4(A: np.ndarray, B: np.ndarray, x: np.ndarray, u: float, dt: float) -> np.ndarray:
    """Perform a single RK4 integration step."""
    Bu = B * u
    k1 = _matvec_auto(A, x) + Bu
    k2 = _matvec_auto(A, x + 0.5 * dt * k1) + Bu
    k3 = _matvec_auto(A, x + 0.5 * dt * k2) + Bu
    k4 = _matvec_auto(A, x + dt * k3) + Bu
    x += (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return x


# =============================================================================
# Performance index
# =============================================================================
@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def iae(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += abs(r[i] - y[i]) * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def ise(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += (r[i] - y[i])**2 * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def itae(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += t[i] * abs(r[i] - y[i]) * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def itse(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += t[i] * (r[i] - y[i])**2 * dt
    return val


# =============================================================================
# Plant Response
# =============================================================================
@njit(float64[:](
    float64[:], float64, float64[:], float64[:],
    float64[:, :], float64[:], float64[:], float64, int64
),
    inline="always"
)
def system_response(t_eval: np.ndarray, dt: float, u_eval: np.ndarray,
                    x: np.ndarray, A: np.ndarray, B: np.ndarray,
                    C: np.ndarray, D: float, solver: int) -> np.ndarray:
    n_steps = len(t_eval)
    y_hist = np.zeros(n_steps)

    for i in range(n_steps):
        u = float(u_eval[i])

        match solver:
            case MySolverInt.RK4:
                x = rk4(A, B, x, u, dt)

        y = dot1D(C, x)
        y_hist[i] = y + D * u

    return y_hist


@njit(inline="always")
def pid_system_response(Kp: float, Ti: float, Td: float, Tf: float,
                        t_eval: np.ndarray, dt: float,
                        r_eval: np.ndarray, l_eval: np.ndarray, n_eval: np.ndarray,
                        x: np.ndarray, control_constraint: np.ndarray,
                        anti_windup_method: int, ka: float,
                        A: np.ndarray, B: np.ndarray, C: np.ndarray, D: float, solver: int
                        ) -> tuple[np.ndarray, np.ndarray]:
    """
    Simulate a SISO system under PID control with reference and two disturbances (Z1, Z2).

    The function advances the plant state and controller states over `t_eval` and
    returns both the control signal history and the measured output trajectory.

    Args:
        Kp: Proportional gain.
        Ti: Integral time constant.
        Td: Derivative time constant.
        Tf: Derivative filter time constant.
        t_eval: Time vector.
        dt: Simulation time step.
        r_eval: Reference trajectory.
        l_eval: Disturbance at plant input (Z1).
        n_eval: Disturbance at measurement/output (Z2).
        x: Initial state vector.
        control_constraint: Control limits [u_min, u_max].
        anti_windup_method: Anti-windup strategy enum value.
        ka: Scaling factor applied to the back-calculation feedback term.
        A: Plant state matrix.
        B: Input matrix.
        C: Output matrix.
        D: Feedthrough scalar.
        solver: Solver enum value.

    Returns:
        u_hist:
            Control signal history u(t), shape (n_steps,).

        y_hist:
            Measured output history y(t), including measurement disturbance and
            feedthrough term, shape (n_steps,).
    """
    e_prev = 0.0
    filtered_prev = 0.0
    integral = 0.0

    u_min = float(control_constraint[0])
    u_max = float(control_constraint[1])

    n_steps = len(t_eval)
    y_hist = np.zeros(n_steps)
    u_hist = np.zeros(n_steps)
    y = dot1D(C, x)

    for i in range(n_steps):
        r = float(r_eval[i])
        l = float(l_eval[i])
        n = float(n_eval[i])

        e = r - (y + n)

        u, integral, filtered_prev = pid_update(
            e, e_prev, filtered_prev, integral, Kp, Ti, Td, Tf,
            dt, u_min, u_max, anti_windup_method, ka
        )

        if solver == MySolverInt.RK4:
            x = rk4(A, B, x, u + l, dt)

        y = dot1D(C, x)

        # Historie: nur das reale Ausgangssignal plus Feedthrough
        u_hist[i] = u
        y_hist[i] = y + n + D * (u + l)

        e_prev = e

    return u_hist, y_hist


@njit(inline="always")
def pid_simulate_metrics(
    Kp: float,
    Ti: float,
    Td: float,
    Tf: float,
    t_eval: np.ndarray,
    dt: float,
    r_eval: np.ndarray,
    l_eval: np.ndarray,
    n_eval: np.ndarray,
    x: np.ndarray,
    control_constraint: np.ndarray,
    anti_windup_method: int,
    ka: float,
    A: np.ndarray,
    B: np.ndarray,
    C: np.ndarray,
    D: float,
    solver: int,
    performance_index: int,
    use_overshoot_control: int,
    overshoot_step_amplitude_abs: float,
    overshoot_step_start_idx: int,
    overshoot_step_sign: float,
    overshoot_r_final: float,
        calculate_max_du_dt: int,
        du_dt_window_steps: int,
) -> tuple[float, float, float]:
    """Simulate one PID candidate and return time-domain evaluation metrics.

    Overshoot is tracked only from the precomputed step start index onward.
    Anti-windup behavior, including back-calculation scaling via ``ka``,
    is applied in the internal PID update step.

    Returns:
        tuple[float, float, float]:
            ``(performance_index_value, overshoot_pct, max_du_dt)``

        ``max_du_dt`` is computed only when ``calculate_max_du_dt`` is enabled.
        It represents the maximum absolute finite-difference control-rate
        estimate over a sliding window of ``du_dt_window_steps`` samples:
        ``max(|u[k] - u[k-m]| / (m * dt))`` with ``m = du_dt_window_steps``.
    """
    e_prev = 0.0
    filtered_prev = 0.0
    integral = 0.0

    u_min = float(control_constraint[0])
    u_max = float(control_constraint[1])

    y = dot1D(C, x)
    perf = 0.0

    max_overshoot = 0.0
    use_ov = use_overshoot_control != 0
    use_du_dt = calculate_max_du_dt != 0
    max_du_dt = np.nan
    window_steps = du_dt_window_steps
    window_dt = 0.0
    u_hist = np.empty(1, dtype=np.float64)
    if use_du_dt:
        max_du_dt = 0.0
        window_dt = float(window_steps) * dt
        u_hist = np.zeros(len(t_eval), dtype=np.float64)

    n_steps = len(t_eval)
    for i in range(n_steps):
        r = float(r_eval[i])
        l = float(l_eval[i])
        n = float(n_eval[i])

        e = r - (y + n)

        u, integral, filtered_prev = pid_update(
            e, e_prev, filtered_prev, integral, Kp, Ti, Td, Tf,
            dt, u_min, u_max, anti_windup_method, ka
        )

        if use_du_dt:
            # Windowed finite-difference estimate of |du/dt|. Using m > 1
            # smooths single-step spikes while preserving the du/dt semantics.
            u_hist[i] = u
            if i >= window_steps:
                du_dt_abs = abs(u - u_hist[i - window_steps]) / window_dt
                if du_dt_abs > max_du_dt:
                    max_du_dt = du_dt_abs

        if solver == MySolverInt.RK4:
            x = rk4(A, B, x, u + l, dt)

        y = dot1D(C, x)
        y_out = y + n + D * (u + l)

        if i > 0:
            err = r - y_out
            if performance_index == PerformanceIndexInt.IAE:
                perf += abs(err) * dt
            elif performance_index == PerformanceIndexInt.ISE:
                perf += err * err * dt
            elif performance_index == PerformanceIndexInt.ITAE:
                perf += t_eval[i] * abs(err) * dt
            elif performance_index == PerformanceIndexInt.ITSE:
                perf += t_eval[i] * err * err * dt

        if use_ov and overshoot_step_amplitude_abs > 0.0 and i >= overshoot_step_start_idx:
            signed_overshoot = overshoot_step_sign * (y_out - overshoot_r_final)
            if signed_overshoot > max_overshoot:
                max_overshoot = signed_overshoot

        e_prev = e

    if (not use_ov) or overshoot_step_amplitude_abs <= 0.0:
        overshoot_pct = np.nan
    else:
        if overshoot_step_start_idx < n_steps:
            if max_overshoot > 0.0:
                overshoot_pct = 100.0 * max_overshoot / overshoot_step_amplitude_abs
            else:
                overshoot_pct = 0.0
        else:
            overshoot_pct = np.inf

    return perf, overshoot_pct, max_du_dt


# =============================================================================
# PSO Function
# =============================================================================
@njit(parallel=True)
def _pid_pso_func(X: np.ndarray, t_eval: np.ndarray, dt: float, r_eval: np.ndarray, l_eval: np.ndarray,
                  n_eval: np.ndarray, A: np.ndarray, B: np.ndarray, C: np.ndarray, D: float,
                  system_order: int, Tf: np.ndarray, control_constraint: np.ndarray, anti_windup_method: int,
                  ka: float, solver: int, performance_index: int,
                  use_overshoot_control: int, overshoot_step_amplitude_abs: float,
                  overshoot_step_start_idx: int, overshoot_step_sign: float,
                  overshoot_r_final: float, calculate_max_du_dt: int,
                  du_dt_window_steps: int, swarm_size: int
                  ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    performance_index_val = np.zeros(swarm_size)
    overshoot_pct = np.full(swarm_size, np.nan)
    max_du_dt = np.full(swarm_size, np.nan)

    for i in prange(swarm_size):
        Kp = float(X[i, 0])
        Ti = float(X[i, 1])
        Td = float(X[i, 2])
        Tf_i = float(Tf[i])

        x = np.zeros(system_order, dtype=np.float64)

        perf_i, overshoot_i, max_du_dt_i = pid_simulate_metrics(
            Kp, Ti, Td, Tf_i,
            t_eval, dt,
            r_eval, l_eval, n_eval,
            x, control_constraint,
            anti_windup_method, ka, A, B, C, D, solver,
            performance_index,
            use_overshoot_control,
            overshoot_step_amplitude_abs,
            overshoot_step_start_idx,
            overshoot_step_sign,
            overshoot_r_final,
            calculate_max_du_dt,
            du_dt_window_steps,
        )
        performance_index_val[i] = perf_i
        overshoot_pct[i] = overshoot_i
        max_du_dt[i] = max_du_dt_i

    return performance_index_val, overshoot_pct, max_du_dt
