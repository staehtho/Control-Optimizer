from typing import Callable
import numpy as np
from .base_function import BaseFunction


class BrownianNoise(BaseFunction):
    """Brownian noise (Wiener process)."""

    def __init__(self) -> None:
        """Initialize Brownian noise with default scale."""
        super().__init__()
        self._param: dict[str, float] = {
            r"\sigma": 1.0  # scale factor
        }
        self._logger.info("BrownianNoise initialized with params: %s", self._param)

    def get_formula(self) -> str:
        return r"B(t) \sim \mathcal{N}(0, \sigma^2 \delta t)"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        sigma = self._param[r"\sigma"]

        def u(t: np.ndarray) -> np.ndarray:
            dt = np.diff(t, prepend=0)
            dt = np.maximum(dt, 1e-12)  # prevent negative/zero
            increments = np.random.normal(0.0, sigma * np.sqrt(dt))
            return np.cumsum(increments)

        return u
