from typing import Callable
import numpy as np
from .base_function import BaseFunction


class PinkNoise(BaseFunction):
    """Approximate pink noise generator (1/f spectrum)."""

    def __init__(self) -> None:
        """Initialize pink noise with default scale."""
        super().__init__()
        self._param: dict[str, float] = {
            r"\sigma": 1.0  # scale factor
        }
        self._logger.info("PinkNoise initialized with params: %s", self._param)

    def get_formula(self) -> str:
        return r"P(f) \sim \frac{1}{f}"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        sigma = self._param[r"\sigma"]

        def u(t: np.ndarray) -> np.ndarray:
            n = len(t)
            num_sources = 16
            array = np.zeros(n)
            random_sources = np.random.randn(num_sources, n)
            for i in range(n):
                array[i] = np.sum(random_sources[:, i])
            return sigma * array / np.max(np.abs(array))

        return u
