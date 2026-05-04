import logging
from typing import Callable

from numpy import ndarray, array

class FrequencyResponseEngine:
    """Engine for frequency-domain analysis of control systems.

    Provides utilities to compute open-loop transfer,
    sensitivity, and complementary sensitivity functions from complex
    frequency responses.
    """

    def __init__(self) -> None:
        """Initialize the frequency response engine with a logger."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FrequencyResponseEngine initialized.")

    def compute(self, tf_func: Callable[[complex | ndarray], complex | ndarray], omega: ndarray) -> ndarray:
        """
        Evaluate a transfer function on the imaginary axis to obtain its
        frequency response.

        Computes L(jω) by calling the provided transfer‑function callable
        `tf_func` with the complex frequency grid s = j·ω.

        Args:
            tf_func: Callable that accepts a complex scalar or ndarray `s`
                and returns the corresponding transfer‑function value(s).
            omega: 1D array of angular frequencies (rad/s) at which the
                transfer function should be evaluated.

        Returns:
            ndarray: Complex frequency response L(jω) evaluated at all
            frequencies in `omega`.
        """

        self._logger.info(
            f"Starting open loop transfer computation (n=%d)",
            omega.size,
        )

        s = 1j * omega
        tf = tf_func(s)

        self._logger.info(
            "Controller transfer computation finished (n=%d)",
            omega.size,
        )

        return array(tf)
