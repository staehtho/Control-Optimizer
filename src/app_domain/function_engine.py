from typing import Callable

from numpy import ndarray


class FunctionEngine:
    """Engine to compute function outputs."""
    @staticmethod
    def compute(t: ndarray, func: Callable[[ndarray], ndarray]) -> ndarray:
        """Compute function values for a given time vector."""
        return func(t)