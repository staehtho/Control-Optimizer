import logging
from dataclasses import dataclass
from typing import Callable
import numpy as np

from app_domain.controlsys import Plant, PIDClosedLoop, AntiWindup, MySolver


@dataclass
class ClosedLoopResponseContext:
    """Input data required to compute a closed-loop time response."""

    num: list[float]
    den: list[float]

    kp: float
    ti: float
    td: float
    tf: float

    t0: float
    t1: float
    dt: float

    solver: MySolver

    anti_windup: AntiWindup
    constraint: tuple[float, float]

    reference: Callable[[np.ndarray], np.ndarray]
    input_disturbance: Callable[[np.ndarray], np.ndarray]
    measurement_disturbance: Callable[[np.ndarray], np.ndarray]


class ClosedLoopResponseEngine:
    """Domain engine for closed-loop response simulation."""

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("ClosedLoopResponseEngine initialized.")

    def compute(self, context: ClosedLoopResponseContext) -> tuple[np.ndarray, np.ndarray]:
        """Compute a closed-loop response for the given simulation context.

        Args:
            context: Closed-loop simulation settings and disturbance signals.

        Returns:
            Tuple (t, y) with simulation time and plant output.
        """
        self._logger.info(
            "Starting closed-loop response computation from %.3f to %.3f (dt=%.6f)",
            context.t0,
            context.t1,
            context.dt,
        )
        plant = Plant(context.num, context.den)

        pid_cl = PIDClosedLoop(
            plant,
            Kp=context.kp,
            Ti=context.ti,
            Td=context.td,
            Tf=context.tf,
            control_constraint=list(context.constraint),
            anti_windup_method=context.anti_windup
        )

        t, y = pid_cl.system_response(
            t0=context.t0,
            t1=context.t1,
            dt=context.dt,
            r=context.reference,
            l=context.input_disturbance,
            n=context.measurement_disturbance,
        )

        self._logger.info(
            "Closed-loop response computation finished (dt=%.6f, t.size=%d, y.size=%d)",
            context.dt,
            t.size,
            y.size,
        )

        return t, y
