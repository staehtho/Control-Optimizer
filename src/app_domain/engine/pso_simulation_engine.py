from dataclasses import dataclass
from typing import Callable, Tuple
import logging
import numpy as np
import sys
import time

from app_domain.controlsys import (
    AntiWindup, ExcitationTarget, PerformanceIndex, MySolver,
    Plant, PIDClosedLoop, PsoFunc, smallest_root_realpart
)
from app_domain.PSO import Swarm


@dataclass
class PsoSimulationParam:
    """Parameter container for PSO-based PID optimization."""

    num: list[float]
    den: list[float]

    t0: float
    t1: float
    dt: float

    solver: MySolver

    anti_windup: AntiWindup
    constraint: tuple[float, float]

    excitation_target: ExcitationTarget
    function: Callable[[np.ndarray], np.ndarray]
    performance_index: PerformanceIndex

    kp: tuple[float, float]
    ti: tuple[float, float]
    td: tuple[float, float]

    swarm_size: int
    pso_iteration: int


@dataclass
class PsoResult:
    """Result container for optimized PID parameters."""

    simulation_time: float
    kp: float
    ti: float
    td: float
    tf: float


class PsoSimulationEngine:
    """Domain-layer engine for PSO-based PID optimization."""

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PsoSimulationEngine initialized.")

    # ==========================================================
    # Public API
    # ==========================================================

    def run_simulation(self, param: PsoSimulationParam, callback: Callable[[int], None]) -> PsoResult:
        """Run full PSO optimization workflow."""

        self._logger.info("Starting PSO simulation.")

        pid_cl, tf = self._create_controller(param)
        r, l, n = self._configure_excitation(param)

        objective = PsoFunc(
            controller=pid_cl,
            t0=param.t0,
            t1=param.t1,
            dt=param.dt,
            r=r,
            l=l,
            n=n,
            solver=param.solver,
            performance_index=param.performance_index,
            swarm_size=param.swarm_size,
            pre_compiling=False
        )

        bounds = self._extract_bounds(param)

        result = self._run_pso(param, objective, bounds, callback)

        # add tf
        result.tf = tf
        self._logger.info("PSO simulation finished.")

        return result

    # ==========================================================
    # Controller Setup
    # ==========================================================

    def _create_controller(self, param: PsoSimulationParam) -> Tuple[PIDClosedLoop, float]:
        """Create plant, PID controller, and set filter time constant."""

        plant = Plant(param.num, param.den)

        pid_cl = PIDClosedLoop(
            plant,
            Kp=10,
            Ti=1,
            Td=1,
            control_constraint=list(param.constraint),
            anti_windup_method=param.anti_windup
        )

        # Determine dominant pole
        p_dom = smallest_root_realpart(plant.den)

        if p_dom >= 0:
            tf = 0.01
        else:
            t_dom = 1 / abs(p_dom)
            tf = t_dom / 100

        pid_cl.set_filter(Tf=tf)

        self._logger.debug("Controller created with Tf=%f", tf)

        return pid_cl, tf

    # ==========================================================
    # Excitation
    # ==========================================================

    def _configure_excitation(self, param: PsoSimulationParam) -> tuple[Callable, Callable, Callable]:
        """Configure excitation signals (r, l, n)."""

        r = lambda t: np.zeros_like(t)
        l = lambda t: np.zeros_like(t)
        n = lambda t: np.zeros_like(t)

        match param.excitation_target:
            case ExcitationTarget.REFERENCE:
                r = param.function
            case ExcitationTarget.INPUT_DISTURBANCE:
                l = param.function
            case ExcitationTarget.MEASUREMENT_DISTURBANCE:
                n = param.function

        self._logger.debug("Excitation configured: %s", param.excitation_target)

        return r, l, n

    # ==========================================================
    # Bounds
    # ==========================================================

    def _extract_bounds(self, param: PsoSimulationParam):
        """Extract parameter bounds for PSO."""

        kp_min, kp_max = param.kp
        ti_min, ti_max = param.ti
        td_min, td_max = param.td

        bounds = [
            [kp_min, ti_min, td_min],
            [kp_max, ti_max, td_max]
        ]

        self._logger.debug("Bounds extracted: %s", bounds)

        return bounds

    # ==========================================================
    # PSO Execution
    # ==========================================================

    def _run_pso(self, param: PsoSimulationParam, objective: PsoFunc, bounds,
                 callback: Callable[[int], None]) -> PsoResult:
        """Execute PSO optimization loop."""

        best_kp = 0.0
        best_ti = 0.0
        best_td = 0.0
        best_cost = sys.float_info.max

        total_start = time.perf_counter()

        for iteration in range(param.pso_iteration):

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
                best_kp, best_ti, best_td = kp, ti, td

            duration = time.perf_counter() - iter_start

            self._logger.info(
                "Iteration %d | duration=%.4fs | J=%.6f | best_J=%.6f",
                iteration + 1, duration, cost, best_cost
            )

            callback(iteration + 1)

        total_duration = time.perf_counter() - total_start

        self._logger.info(
            "PSO finished | total_duration=%.4fs | best_J=%.6f",
            total_duration, best_cost
        )

        return PsoResult(
            simulation_time=total_duration,
            kp=best_kp,
            ti=best_ti,
            td=best_td,
            tf=0.0  # default !!!
        )
