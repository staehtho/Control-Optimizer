from typing import Callable

import numpy as np
from PySide6.QtCore import QT_TRANSLATE_NOOP

from .base_function import BaseFunction


class SineFunction(BaseFunction):
    """Sine function u(t) = A*sin(ωt + φ) + y0."""

    LABEL = QT_TRANSLATE_NOOP("Function", "Sine function")

    def __init__(self) -> None:
        """Initialize sine function with default parameters."""
        super().__init__()
        self._param: dict[str, float] = {
            r"A": 1.0,
            r"\omega": 1.0,
            r"\varphi": 0.0,
            r"u_0": 0.0
        }
        self._logger.info("SineFunction initialized with params: %s", self._param)

    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        return r"u(t) = A \cdot \sin(\omega t + \varphi) + u_0"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized sine function using current parameters."""
        a = self._param[r"A"]
        omega = self._param[r"\omega"]
        varphi = self._param[r"\varphi"]
        u0 = self._param[r"u_0"]

        def u(t: np.ndarray) -> np.ndarray:
            return a * np.sin(omega * t + varphi) + u0

        return u