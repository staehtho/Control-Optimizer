import logging
from abc import ABC, abstractmethod
from typing import Callable

from numpy import ndarray


class BaseFunction(ABC):
    """Abstract base class for mathematical functions.

    Stores parameters and computed vectors t and y, provides
    logging for parameter changes.
    """

    def __init__(self) -> None:
        """Initialize function parameters and logger."""
        self._param: dict[str, float] = {}
        self._logger = logging.getLogger(f"Function.{self.__class__.__name__}")
        self._logger.debug("BaseFunction initialized")

    def __repr__(self) -> str:
        """Return a string representation of the function and its parameters."""
        return f"{self.__class__.__name__}(" + ", ".join([f"{key}={val}" for key, val in self._param.items()]) + ")"

    def update_param_value(self, key: str, value: float) -> None:
        """Update or add a parameter value.

        Args:
            key: Parameter name.
            value: Parameter value.
        """
        old = self._param.get(key, None)
        self._param[key] = value
        self._logger.debug("Param updated: %s=%s (was %s)", key, value, old)

    def get_param_value(self, key: str) -> float:
        """Return the value of a parameter.

        Args:
            key: Parameter name.

        Returns:
            Parameter value or 0 if not set.
        """
        value = self._param.get(key, 0)
        self._logger.debug("Param requested: %s=%s", key, value)
        return value

    def get_param(self) -> dict[str, float]:
        """Return all parameters as a dictionary."""
        self._logger.debug("Returning all params: %s", self._param)
        return self._param

    def copy(self) -> BaseFunction:
        """Return a copy of the current function instance."""
        cloned = self.__class__()
        cloned._param = self._param.copy()
        return cloned

    @abstractmethod
    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        ...

    @abstractmethod
    def get_function(self) -> Callable[[ndarray], ndarray]:
        """Return a callable that computes y(t)."""
        ...
