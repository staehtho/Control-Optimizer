from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional
import logging
import numpy as np
import sys
import time

from app_domain.controlsys import ExcitationTarget, Plant, ControllerType
from app_domain.pso_objective import PsoFunc, compute_effective_tf_report, TfLimitReport
from app_domain.PSO import Swarm
from app_types import PsoResult
from app_domain.functions import resolve_function_type, FunctionTypes

if TYPE_CHECKING:
    from app_types import PsoSimulationParam
    from app_domain.controlsys import ClosedLoop

class PsoSimulationEngine:
    """Domain-layer engine for PSO-based PID optimization."""

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PsoSimulationEngine initialized.")

        self._total_duration = 0.0

        self._best_params = []

    # ==========================================================
    # Public API
    # ==========================================================

    def run_simulation(
            self,
            param: PsoSimulationParam,
            callback: Callable[[int], None],
            should_stop: Optional[Callable[[], bool]] = None,
    ) -> PsoResult:
        """Run full PSO optimization workflow."""

        self._logger.info("Starting PSO simulation.")

        cl = self._create_controller(param)
        r, l, n = self._configure_excitation(param)

        use_freq_metrics = param.gain_margin_enabled or param.phase_margin_enabled or param.stability_margin_enabled

        objective = PsoFunc(
            controller=cl,
            t0=param.t0,
            t1=param.t1,
            dt=param.dt,
            r=r,
            l=l,
            n=n,
            solver=param.solver,
            swarm_size=param.swarm_size,
            tf_tuning_factor_n=param.tuning_factor,
            tf_limit_factor_k=param.limit_factor,
            sampling_rate_hz=param.sampling_rate,
            performance_index=param.error_criterion,
            use_overshoot_control=param.overshoot_control_enabled,
            allowed_overshoot_pct=param.overshoot_control if param.overshoot_control_enabled else 10000,
            use_max_du_dt_constraint=param.slew_rate_limit_enabled,
            allowed_max_du_dt=param.slew_rate_max,
            du_dt_window_steps=param.slew_window_size,
            use_freq_metrics=use_freq_metrics,
            gm_min_db=param.gain_margin if param.gain_margin_enabled else 0,
            pm_min_deg=param.phase_margin if param.phase_margin_enabled else 0,
            ms_max_db=param.stability_margin if param.stability_margin_enabled else None,
            freq_low_exp=param.omega_exp_low,
            freq_high_exp=param.omega_exp_high,
            freq_points=param.omega_points,
            pre_compiling=False,
        )

        self._run_pso(param, objective, callback, should_stop)

        self._logger.info("PSO simulation finished.")
        return self._evaluate_pso_result(param, objective)

    # ==========================================================
    # Controller Setup
    # ==========================================================
    @staticmethod
    def _create_controller(param: PsoSimulationParam) -> ClosedLoop:
        """Create plant, PID controller, and set filter time constant."""

        plant = Plant(param.num, param.den)

        return param.controller_class(
            plant,
            control_constraint=list(param.constraint),
            anti_windup_method=param.anti_windup,
            ka=param.ka
        )

    # ==========================================================
    # Excitation
    # ==========================================================
    @staticmethod
    def _configure_excitation(param: PsoSimulationParam) -> tuple[Callable, Callable, Callable]:
        """Configure excitation signals (r, l, n)."""

        r = lambda t: np.zeros_like(t)
        l = lambda t: np.zeros_like(t)
        n = lambda t: np.zeros_like(t)

        match param.excitation_target:
            case ExcitationTarget.REFERENCE:
                r = param.function.get_function()
            case ExcitationTarget.INPUT_DISTURBANCE:
                l = param.function.get_function()
            case ExcitationTarget.MEASUREMENT_DISTURBANCE:
                n = param.function.get_function()

        return r, l, n

    # ==========================================================
    # PSO Execution
    # ==========================================================
    def _run_pso(
            self,
            param: PsoSimulationParam,
            objective: PsoFunc,
            callback: Callable[[int], None],
            should_stop: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Execute PSO optimization loop."""

        self._total_duration = 0.0

        self._best_params = []

        best_cost = sys.float_info.max

        total_start = time.perf_counter()

        for iteration in range(param.pso_iteration):
            if should_stop is not None and should_stop():
                self._logger.info("PSO simulation interrupted before iteration %d.", iteration + 1)
                raise InterruptedError("PSO simulation interrupted")

            iter_start = time.perf_counter()

            swarm = Swarm(
                objective,
                param.swarm_size,
                param.n_param,
                list(param.bounds),
                **param.hyperparameters.__dict__
            )

            params, cost = swarm.simulate_swarm()

            if cost < best_cost:
                best_cost = cost
                self._best_params = params

            duration = time.perf_counter() - iter_start

            self._logger.info(
                "Iteration %d | duration=%.4fs | J=%.6f | best_J=%.6f",
                iteration + 1, duration, cost, best_cost
            )

            callback(iteration + 1)

            if should_stop is not None and should_stop():
                self._logger.info("PSO simulation interrupted after iteration %d.", iteration + 1)
                raise InterruptedError("PSO simulation interrupted")

        self._total_duration = time.perf_counter() - total_start

        self._logger.info(
            "PSO finished | total_duration=%.4fs | best_J=%.6f",
            self._total_duration, best_cost
        )

    # ==========================================================
    # PSO Result
    # ==========================================================
    def _evaluate_pso_result(
            self,
            param: PsoSimulationParam,
            objective: PsoFunc,
    ) -> PsoResult:
        """evaluate PSO result."""

        # set the calculation flag
        objective.set_calculate_max_du_dt(True)
        objective.set_calculate_overshoot(True)
        objective.set_calculate_freq_metrics(True)

        tf_report = self._evaluate_tf(param)

        has_tf = True
        if tf_report is None:
            has_tf = False
            tf_report = TfLimitReport(0, 0, 0, 0, 0, False, False, False, 0)

        # result time domain
        eval_result = objective.evaluate_candidates(np.array([self._best_params]))

        show_overshoot = resolve_function_type(param.function) == FunctionTypes.STEP

        params = {k: v for k, v in zip(param.controller_param_names, self._best_params)}

        if has_tf:
            params["Tf"] = float(tf_report.tf_effective)

        return PsoResult(
            simulation_time=self._total_duration,
            best_params=params,
            has_tf=has_tf,
            tf_limited_simulation=tf_report.limited_by_simulation,
            tf_limited_sampling=tf_report.limited_by_sampling,
            min_sampling_rate=tf_report.min_sampling_rate_hz,
            t0=param.t0,
            t1=param.t1,
            is_feasible=bool(eval_result.feasible[0]),
            error_criterion=float(eval_result.perf[0]),
            overshoot=float(eval_result.overshoot_pct[0]),
            show_overshoot=show_overshoot,
            slew_rate=float(eval_result.max_du_dt[0]),
            gain_margin=float(eval_result.gm_db[0]),
            omega_180=float(eval_result.w180[0]),
            has_omega_180=bool(eval_result.has_w180[0]),
            phase_margin=float(eval_result.pm_deg[0]),
            omega_c=float(eval_result.wc[0]),
            has_omega_c=bool(eval_result.has_wc[0]),
            stability_margin=float(eval_result.ms_db[0]),
        )

    def _evaluate_tf(
            self,
            param: PsoSimulationParam,
    ) -> TfLimitReport | None:
        """Evaluate Tf report."""

        match param.controller_type:
            case ControllerType.PI:
                Td = None
            case ControllerType.PID:
                Td = float(self._best_params[2])
            case _:
                raise NotImplementedError(
                    f"Controller type '{param.controller_type}' is not defined in tf evaluation."
                )

        if Td is None:
            return None

        return compute_effective_tf_report(
            Td=Td,
            dt=param.dt,
            tf_tuning_factor_n=param.tuning_factor,
            tf_limit_factor_k=param.limit_factor,
            sampling_rate_hz=param.sampling_rate,
        )
