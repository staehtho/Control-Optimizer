import logging
from typing import Callable

from numpy import ndarray
from dataclasses import dataclass

from app_domain.controlsys import Plant, MySolver


@dataclass
class PlantResponseContext:
    """Context for plant response computation."""

    num: list[float]
    den: list[float]

    t0: float
    t1: float

    solver: MySolver

    reference: Callable[[ndarray], ndarray]


class PlantResponseEngine:
    """Domain engine that computes a plant response.

    The class contains pure simulation logic and is independent from Qt,
    threads, and UI concerns.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PlantResponseEngine initialized.")

    def compute(self, context: PlantResponseContext) -> tuple[
        ndarray, ndarray]:
        """Compute the plant step response for the given transfer function.

        Args:
            context: Plant simulation settings and disturbance signal

        Returns:
            tuple[np.ndarray, np.ndarray]:
                A tuple containing:

                - **t** (*np.ndarray*): Simulation time vector.
                - **y** (*np.ndarray*): Measured plant output y(t).
        """
        self._logger.info("Starting step response computation from %.3f to %.3f", context.t0, context.t1)
        dt = (context.t1 - context.t0) / 5000
        plant = Plant(context.num, context.den)
        t, y = plant.system_response(context.reference, context.t0, context.t1, dt, solver=context.solver)
        self._logger.info(
            "Step response computation finished (dt=%.6f, t.size=%d, y.size=%d)",
            dt,
            t.size,
            y.size,
        )
        return t, y
