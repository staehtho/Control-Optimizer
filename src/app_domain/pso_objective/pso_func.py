import math
from typing import Callable

import numpy as np

from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.controlsys.closedLoop import ClosedLoop
from app_domain.controlsys.enums import *

from .freq_metrics import compute_loop_metrics_batch
from .filter_time_constant_handler import (
    TfLimitReport, compute_effective_tf_report, compute_effective_tf_batch,
    normalize_positive_scalar, normalize_sampling_rate_hz
)
from .time_domain_numba import pid_pso_func


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

    Optional time-domain maximum slew-rate handling:
      - ``calculate_max_du_dt`` enables ``max_du_dt`` as a diagnostic metric.
      - ``use_max_du_dt_constraint`` applies the measured metric as an
        additional feasibility constraint.
      - ``max_du_dt`` is the maximum absolute control-rate estimate over a
        sliding window of ``m`` simulation steps:
        ``max(|u[k] - u[k-m]| / (m * dt))``.

    Constraints (policies):
      - PM is minimum only: PM >= PM_min_deg
        If PM missing (has_wc=False) => infeasible.
      - GM is minimum only: GM_dB >= GM_min_db
        If GM missing => GM=+inf => OK (violation 0).
      - Ms is maximum in dB: Ms <= Ms_max_db
      - Non-finite frequency responses are treated as infeasible (guarded by freq_metrics).
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

            cost is interpreted as:
              - J for feasible candidates
              - V for infeasible candidates
        """
        self.controller = controller

        self.t0 = t0
        self.t1 = t1
        self.dt = dt
        self.t_eval = np.arange(t0, t1 + dt, dt)
        self.tf_tuning_factor_n = normalize_positive_scalar(tf_tuning_factor_n, "tf_tuning_factor_n")
        self.tf_limit_factor_k = normalize_positive_scalar(tf_limit_factor_k, "tf_limit_factor_k")
        self.sampling_rate_hz = normalize_sampling_rate_hz(sampling_rate_hz)

        # Toggle frequency-domain metrics/constraints
        self.use_freq_metrics = bool(use_freq_metrics)

        if self.use_freq_metrics:
            self._freq_low_exp = float(freq_low_exp)
            self._freq_high_exp = float(freq_high_exp)
            self._freq_points = int(freq_points)

            self._w = np.logspace(self._freq_low_exp, self._freq_high_exp, self._freq_points).astype(np.float64)
            self._s = 1j * self._w
            self._G = np.asarray(self.controller.plant.system(self._s), dtype=np.complex128)

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
        if pre_compiling:
            X = np.array([[10.0, 9.6, 0.3] for _ in range(swarm_size)], dtype=np.float64)
            _ = self.__call__(X)

    def __call__(self, X: np.ndarray) -> np.ndarray:
        """Backward-compatible scalar objective interface."""
        return self.evaluate_candidates(X)["cost"]

    def evaluate_tf_for_td(self, Td: float) -> TfLimitReport:
        return compute_effective_tf_report(
            Td=Td,
            dt=self.dt,
            tf_tuning_factor_n=self.tf_tuning_factor_n,
            tf_limit_factor_k=self.tf_limit_factor_k,
            sampling_rate_hz=self.sampling_rate_hz,
        )

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

    def evaluate_candidates(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """
        Evaluate candidates and expose both scalar cost and feasibility-aware data.

        Args:
            X: PID parameter matrix of shape (P, 3). Each row contains [Kp, Ti, Td].

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

        _, Tf = compute_effective_tf_batch(
            Td=X[:, 2],
            dt=self.dt,
            tf_tuning_factor_n=self.tf_tuning_factor_n,
            tf_limit_factor_k=self.tf_limit_factor_k,
            sampling_rate_hz=self.sampling_rate_hz,
        )

        # --------------------------------------------------
        # 1) Optional: Frequency metrics + constraint violation
        # --------------------------------------------------
        if self.use_freq_metrics:
            tf_copy = Tf.copy()
            with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
                metrics = compute_loop_metrics_batch(
                    plant=self.controller.plant,
                    controller_class=type(self.controller),
                    X=np.hstack([X, tf_copy.reshape(tf_copy.shape[0], 1)]),
                    w=self._w,
                )

            V = self._compute_violation_batch(metrics)
        else:
            # No frequency-domain constraints -> all candidates feasible.
            V = np.zeros(P, dtype=np.float64)

        V_ov = np.zeros(P, dtype=np.float64)
        V_du = np.zeros(P, dtype=np.float64)

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

            perf_vals, overshoot_vals, max_du_dt_vals = pid_pso_func(
                Xf, self.t_eval, self.dt, self.r_eval, self.l_eval,
                self.n_eval, self.A, self.B, self.C, self.D,
                self.plant_order, Tf[feasible],
                self.control_constraint, self.anti_windup_method,
                self.ka, self.solver, self.performance_index,
                1 if compute_overshoot else 0,
                self._overshoot_step_amplitude_abs,
                self._overshoot_step_start_idx,
                self._overshoot_step_sign, self._overshoot_r_final,
                1 if compute_max_du_dt else 0,
                self.du_dt_window_steps, Pf
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

        return {
            "cost": cost,
            "feasible": feasible_final,
            "violation": V_total,
            "perf": perf,
            "overshoot_pct": overshoot_pct,
            "max_du_dt": max_du_dt,
        }

    def set_calculate_max_du_dt(self, value: bool) -> None:
        self.calculate_max_du_dt = value

        self._update_max_du_dt_cache()

    def set_calculate_overshoot(self, value: bool) -> None:
        self.calculate_overshoot = value

        self._update_overshoot_control_cache()
