from typing import Callable

import numpy as np
from PySide6.QtCore import QT_TRANSLATE_NOOP

from .base_function import BaseFunction


class StepFunction(BaseFunction):
    """General step function u(t) = λ * σ(t - t0)."""
    LABEL = QT_TRANSLATE_NOOP("Function", "Step function")

    def __init__(self) -> None:
        """Initialize a general step function."""

        super().__init__()

        self._param: dict[str, float] = {
            r"\lambda": 1.0,
            r"t_0": 0.0
        }
        self._logger.info("StepFunction initialized with params: %s", self._param)

    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        return r"u(t) = \lambda \cdot \sigma(t - t_0)"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized function computing the step."""
        amplitude = self._param[r"\lambda"]
        t0 = self._param[r"t_0"]

        def u(t: np.ndarray) -> np.ndarray:
            return amplitude * np.where(t >= t0, 1.0, 0.0)

        return u