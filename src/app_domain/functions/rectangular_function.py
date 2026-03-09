from typing import Callable

import numpy as np

from .base_function import BaseFunction


class RectangularFunction(BaseFunction):
    """Rectangular function with duty cycle."""

    def __init__(self) -> None:
        """Initialize rectangular function with default parameters."""
        super().__init__()
        self._param: dict[str, float] = {
            r"A": 1.0,
            r"\omega": 1.0,
            r"\varphi": 0.0,
            r"D": 0.5,  # duty cycle (0..1)
            r"u_0": 0.0
        }
        self._logger.info(
            "RectangularFunction initialized with params: %s", self._param
        )

    def get_formula(self) -> str:
        """Return a string representation of the function."""
        return r"u(t) = A \cdot \mathrm{rect}(\omega t + \varphi, D) + u_0"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized rectangular function."""
        a = self._param[r"A"]
        omega = self._param[r"\omega"]
        varphi = self._param[r"\varphi"]
        d = self._param[r"D"]
        u0 = self._param[r"u_0"]

        def u(t: np.ndarray) -> np.ndarray:
            phase = np.mod(omega * t + varphi, 2 * np.pi)
            return np.where(phase < 2 * np.pi * d, a + u0, u0)

        return u
