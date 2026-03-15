from typing import Callable
import numpy as np
from .base_function import BaseFunction


class WhiteNoise(BaseFunction):
    """White noise generator: Gaussian with zero mean by default."""

    def __init__(self) -> None:
        """Initialize white noise with default parameters."""
        super().__init__()
        self._param: dict[str, float] = {
            r"\mu": 0.0,  # mean
            r"\sigma": 1.0  # standard deviation
        }
        self._logger.info("WhiteNoise initialized with params: %s", self._param)

    def get_formula(self) -> str:
        return r"W(t) \sim \mathcal{N}(\mu, \sigma^2)"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        mu = self._param[r"\mu"]
        sigma = self._param[r"\sigma"]

        def u(t: np.ndarray) -> np.ndarray:
            return np.random.normal(mu, sigma, size=t.shape)

        return u
