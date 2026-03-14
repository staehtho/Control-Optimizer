from typing import Callable
import logging
from numpy import ndarray


class FunctionEngine:
    """Engine to compute function outputs (Domain Layer).

    This class performs the core calculation of a function output vector
    given an input time vector. It is Qt- and Thread-free.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FunctionEngine initialized.")

    def compute(self, t: ndarray, func: Callable[[ndarray], ndarray]) -> ndarray:
        """Compute the function output vector.

        Args:
            t: Input time vector.
            func: Callable function mapping t -> y.

        Returns:
            np.ndarray: Computed output vector.
        """
        self._logger.info("Starting function computation for t.size=%d", t.size)
        y = func(t)
        self._logger.info("Function computation finished. Output size=%d", y.size)
        return y
