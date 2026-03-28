from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Tuple, Optional
import logging
import numpy as np
import sys
import time

from app_domain.controlsys import ExcitationTarget, Plant, PIDClosedLoop, PsoFunc, compute_effective_tf_report
from app_domain.PSO import Swarm
from app_types import PsoResult

if TYPE_CHECKING:
    from app_types import PsoSimulationParam

class PsoSimulationEngine:
    """Domain-layer engine for PSO-based PID optimization."""

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PsoSimulationEngine initialized.")

        self._total_duration = 0.0

        self._best_kp = 0.0
        self._best_ti = 0.0
        self._best_td = 0.0

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

        pid_cl = self._create_controller(param)
        r, l, n = self._configure_excitation(param)

        use_freq_metrics = param.gain_margin_enabled or param.phase_margin_enabled or param.stability_margin_enabled

        objective = PsoFunc(
            controller=pid_cl,
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
            allowed_overshoot_pct=param.overshoot_control if param.overshoot_control_enabled else 0,
            use_control_activity_constraint=param.slew_rate_limit_enabled,
            allowed_control_activity=param.slew_rate_max,
            use_freq_metrics=use_freq_metrics,
            freq_low_exp=-5,  # TODO temp value
            freq_high_exp=5,  # TODO temp value
            freq_points=450,  # TODO temp value
            gm_min_db=param.gain_margin if param.gain_margin_enabled else 0,
            pm_min_deg=param.phase_margin if param.phase_margin_enabled else 0,
            ms_max_db=param.stability_margin if param.stability_margin_enabled else None,
            pre_compiling=False,
        )

        bounds = self._extract_bounds(param)

        self._run_pso(param, objective, bounds, callback, should_stop)

        self._logger.info("PSO simulation finished.")

        return PsoResult(
            simulation_time=self._total_duration,
            kp=self._best_kp,
            ti=self._best_ti,
            td=self._best_td,
            tf=0,
            t0=param.t0,
            t1=param.t1
        )

    # ==========================================================
    # Controller Setup
    # ==========================================================
    @staticmethod
    def _create_controller(param: PsoSimulationParam) -> PIDClosedLoop:
        """Create plant, PID controller, and set filter time constant."""

        plant = Plant(param.num, param.den)

        pid_cl = PIDClosedLoop(
            plant,
            Kp=10,
            Ti=1,
            Td=1,
            control_constraint=list(param.constraint),
            anti_windup_method=param.anti_windup,
            ka=param.ka
        )

        return pid_cl

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
    # Bounds
    # ==========================================================
    @staticmethod
    def _extract_bounds(param: PsoSimulationParam):
        """Extract parameter bounds for PSO."""

        kp_min, kp_max = param.kp
        ti_min, ti_max = param.ti
        td_min, td_max = param.td

        bounds = [
            [kp_min, ti_min, td_min],
            [kp_max, ti_max, td_max]
        ]

        return bounds

    # ==========================================================
    # PSO Execution
    # ==========================================================

    def _run_pso(
            self,
            param: PsoSimulationParam,
            objective: PsoFunc,
            bounds,
            callback: Callable[[int], None],
            should_stop: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Execute PSO optimization loop."""

        self._total_duration = 0.0

        self._best_kp = 0.0
        self._best_ti = 0.0
        self._best_td = 0.0
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
                3,
                bounds
            )

            result, cost = swarm.simulate_swarm()
            kp, ti, td = result

            if cost < best_cost:
                best_cost = cost
                self._best_kp, self._best_ti, self._best_td = kp, ti, td

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

