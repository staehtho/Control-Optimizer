import logging
from numpy import ndarray

from app_domain.controlsys import Plant, MySolver


class PlantStepResponseEngine:
    """Domain engine that computes a plant step response.

    The class contains pure simulation logic and is independent from Qt,
    threads, and UI concerns.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PlantStepResponseEngine initialized.")

    def compute(self, num: list[float], den: list[float], t0: float, t1: float, solver: MySolver) -> tuple[
        ndarray, ndarray]:
        """Compute the plant step response for the given transfer function.

        Args:
            num: Plant numerator coefficients.
            den: Plant denominator coefficients.
            t0: Start time.
            t1: End time.
            solver: Numerical solver used by the simulation backend.

        Returns:
            Tuple (t, y) containing the time vector and output response.
        """
        self._logger.info("Starting step response computation from %.3f to %.3f", t0, t1)
        dt = (t1 - t0) / 5000
        plant = Plant(num, den)
        t, y = plant.step_response(t0, t1, dt, solver)
        self._logger.info(
            "Step response computation finished (dt=%.6f, t.size=%d, y.size=%d)",
            dt,
            t.size,
            y.size,
        )
        return t, y
