from typing import Callable
import numpy as np

from .base_function import BaseFunction


class NullFunction(BaseFunction):
    """Null function u(t) = 0."""

    def __init__(self) -> None:
        """Initialize null function with no active parameters."""
        super().__init__()
        self._param: dict[str, float] = {}
        self._logger.info("NullFunction initialized")

    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        return r"u(t) = 0"

    def get_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized zero function."""

        def u(t: np.ndarray) -> np.ndarray:
            return np.zeros_like(t)

        return u
