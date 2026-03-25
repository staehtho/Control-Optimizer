from __future__ import annotations
from typing import TYPE_CHECKING
import logging
import numpy as np

from app_domain.controlsys import Plant, PIDClosedLoop

if TYPE_CHECKING:
    from app_types import ClosedLoopResponseContext

class ClosedLoopResponseEngine:
    """Domain engine for closed-loop response simulation."""

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("ClosedLoopResponseEngine initialized.")

    def compute(self, context: ClosedLoopResponseContext) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute a closed-loop response for the given simulation context.

        Args:
            context: Closed-loop simulation settings and disturbance signals.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray]:
                A tuple containing:

                - **t** (*np.ndarray*): Simulation time vector.
                - **u** (*np.ndarray*): Control signal history u(t).
                - **y** (*np.ndarray*): Measured plant output y(t).
        """
        self._logger.info(
            "Starting closed-loop response computation from %.3f to %.3f",
            context.t0, context.t1
        )
        plant = Plant(context.num, context.den)

        pid_cl = PIDClosedLoop(
            plant,
            Kp=context.kp,
            Ti=context.ti,
            Td=context.td,
            Tf=context.tf,
            control_constraint=list(context.constraint),
            anti_windup_method=context.anti_windup,
            ka=context.ka
        )
        dt = (context.t1 - context.t0) / 5000
        t, u, y = pid_cl.system_response(
            t0=context.t0,
            t1=context.t1,
            dt=dt,
            r=context.reference,
            l=context.input_disturbance,
            n=context.measurement_disturbance,
        )

        self._logger.info(
            "Closed-loop response computation finished (t.size=%d, y.size=%d)",
            t.size, y.size,
        )

        return t, u, y

