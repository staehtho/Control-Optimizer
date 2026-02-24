from numpy import ndarray
import logging


from .controlsys import Plant, MySolver


class PlantStepResponseEngine:
    """Engine to compute the step response of a Plant (Domain Layer).

    This class contains the core computation logic. It is Qt-free and
    does not handle threading or UI signals.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PlantStepResponseEngine initialized.")

    def compute(self, num: list[float], den: list[float], t0: float, t1: float, solver: MySolver) -> tuple[
        ndarray, ndarray]:
        """Compute step response for the given plant coefficients.

        Args:
            num: Numerator coefficients of the plant.
            den: Denominator coefficients of the plant.
            t0: Start time.
            t1: End time.
            solver: Solver instance for simulation.

        Returns:
            Tuple (t, y) of time vector and step response.
        """
        self._logger.info("Starting step response computation from %.3f to %.3f", t0, t1)
        dt = (t1 - t0) / 5000
        plant = Plant(num, den)
        t, y = plant.step_response(t0, t1, dt, solver)
        self._logger.info("Step response computation finished. t.size=%d, y.size=%d", t.size, y.size)
        return t, y