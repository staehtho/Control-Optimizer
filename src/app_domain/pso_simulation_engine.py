from dataclasses import dataclass
from typing import Callable
import logging
import numpy as np
import sys

from app_domain.controlsys import (
    AntiWindup, ExcitationTarget, PerformanceIndex, MySolver, Plant, PIDClosedLoop, PsoFunc,
    smallest_root_realpart
)
from app_domain.PSO import Swarm

@dataclass
class PsoSimulationParam:
    num: list[float]
    den: list[float]

    t0: float
    t1: float
    dt: float

    solver: MySolver

    anti_windup: AntiWindup
    constraint: tuple[float, float]

    excitation_target: ExcitationTarget
    function: Callable[[float], float]
    performance_index: PerformanceIndex

    kp: tuple[float, float]
    ti: tuple[float, float]
    td: tuple[float, float]

    swarm_size: int
    pso_iteration: int


@dataclass
class PsoResult:
    kp: float
    ti: float
    td: float
    tf: float

class PsoSimulationEngine:


    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FunctionEngine initialized.")

    def run_simulation(self, pso_simulation_param: PsoSimulationParam, callback: Callable[[], None]) -> PsoResult:

        plant = Plant(pso_simulation_param.num, pso_simulation_param.den)
        pid_cl = PIDClosedLoop(
            plant, Kp=10, Ti=1, Td=1, control_constraint=list(pso_simulation_param.constraint),
            anti_windup_method=pso_simulation_param.anti_windup
        )

        r = lambda t: np.zeros_like(t)
        l = lambda t: np.zeros_like(t)
        n = lambda t: np.zeros_like(t)

        match pso_simulation_param.excitation_target:
            case ExcitationTarget.REFERENCE:
                r = pso_simulation_param.function
            case ExcitationTarget.INPUT_DISTURBANCE:
                l = pso_simulation_param.function
            case ExcitationTarget.MEASUREMENT_DISTURBANCE:
                n = pso_simulation_param.function

        # dominant pole (least negative real part)
        p_dom = smallest_root_realpart(plant.den)

        # find corresponding time constant to dominant pole and set filter time constant
        if p_dom >= 0:
            pid_cl.set_filter(Tf=0.01)
            tf = 0.01
        else:
            t_dom = 1 / abs(p_dom)
            pid_cl.set_filter(Tf=t_dom / 100)
            tf = t_dom / 100

        pos_func = PsoFunc(
            controller=pid_cl,
            t0=pso_simulation_param.t0,
            t1=pso_simulation_param.t1,
            dt=pso_simulation_param.dt,
            r=r, l=l, n=n,
            solver=pso_simulation_param.solver,
            performance_index=pso_simulation_param.performance_index,
        )

        kp_min, kp_max = pso_simulation_param.kp
        ti_min, ti_max = pso_simulation_param.ti
        td_min, td_max = pso_simulation_param.td

        bounds = [[kp_min, ti_min, td_min], [kp_max, ti_max, td_max]]

        # init values
        best_Kp = 0
        best_Ti = 0
        best_Td = 0
        best_performance_index = sys.float_info.max

        for _ in range(pso_simulation_param.pso_iteration):
            swarm = Swarm(pos_func, pso_simulation_param.swarm_size, 3, bounds)
            swarm_result, performance_index_val = swarm.simulate_swarm()

            # Best parameters from the swarm
            Kp = swarm_result[0]
            Ti = swarm_result[1]
            Td = swarm_result[2]

            if performance_index_val < best_performance_index:
                best_performance_index = performance_index_val
                best_Kp = Kp
                best_Ti = Ti
                best_Td = Td

        return PsoResult(kp=best_Kp, ti=best_Ti, td=best_Td, tf=tf)
