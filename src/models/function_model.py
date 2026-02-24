from PySide6.QtCore import QObject, QThread, Signal, Slot, Property, QT_TRANSLATE_NOOP
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable
import logging
import sys


class FunctionComputeThread(QThread):
    """Thread to compute function outputs asynchronously.

    Attributes:
        _t (np.ndarray): Input time vector.
        _y (np.ndarray): Computed function values.
        _func (Callable): Function to compute y from t.
        _logger (logging.Logger): Logger for this thread.
    """

    def __init__(self, t: np.ndarray, func: Callable[[np.ndarray], np.ndarray]) -> None:
        """Initialize the thread with input vector and function.

        Args:
            t: Input time vector.
            func: Function to compute output values.
        """
        super().__init__()
        self._t = t
        self._y = np.zeros_like(t)
        self._func = func
        self._logger = logging.getLogger(f"Thread.{self.__class__.__name__}")
        self._logger.debug("Initialized with t.size=%d", t.size)

    def run(self):
        """Run the computation in a separate thread."""
        self._logger.info("Computation started")
        self._y = self._func(self._t)
        self._logger.info("Computation finished with y.size=%d", self._y.size)

    def get_result(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the input and computed output vectors.

        Returns:
            Tuple containing (t, y).
        """
        return self._t, self._y


class BaseFunction(ABC):
    """Abstract base class for mathematical functions.

    Stores parameters and computed vectors t and y, provides
    logging for parameter changes.
    """
    TRANSLATION_CONTEXT = "FunctionModel"
    LABEL: object = None

    def __init__(self) -> None:
        """Initialize function parameters and logger."""
        self._param: dict[str, float] = {}
        self._t: np.ndarray = np.array([])
        self._y: np.ndarray = np.array([])
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

    @property
    def t(self) -> np.ndarray:
        """Return input vector t."""
        return self._t

    @t.setter
    def t(self, value: np.ndarray) -> None:
        """Set input vector t."""
        self._t = value

    @property
    def y(self) -> np.ndarray:
        """Return computed output vector y."""
        return self._y

    @y.setter
    def y(self, value: np.ndarray) -> None:
        """Set computed output vector y."""
        self._y = value

    @abstractmethod
    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        ...

    @abstractmethod
    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a callable that computes y(t)."""
        ...


class UnitStepFunction(BaseFunction):
    """Unit step function u(t)."""
    LABEL = QT_TRANSLATE_NOOP("FunctionModel", "Unit step function")

    def __init__(self) -> None:
        """Initialize unit step function."""
        super().__init__()
        self._logger.info("UnitStepFunction initialized")

    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        return r"u = \sigma(t)"

    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized function computing the unit step."""
        def u(t: np.ndarray) -> np.ndarray:
            return np.where(t >= 0, 1.0, 0.0)
        return u


class SineFunction(BaseFunction):
    """Sine function u(t) = A*sin(ωt + φ) + y0."""

    LABEL = QT_TRANSLATE_NOOP("FunctionModel", "Sine function")

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

    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized sine function using current parameters."""
        a = self._param[r"A"]
        omega = self._param[r"\omega"]
        varphi = self._param[r"\varphi"]
        u0 = self._param[r"u_0"]

        def u(t: np.ndarray) -> np.ndarray:
            return a * np.sin(omega * t + varphi) + u0

        return u

class CosineFunction(BaseFunction):
    """Cosine function u(t) = A*cos(ωt + φ) + y0."""

    LABEL = QT_TRANSLATE_NOOP("FunctionModel", "Cosine function")

    def __init__(self) -> None:
        """Initialize sine function with default parameters."""
        super().__init__()
        self._param: dict[str, float] = {
            r"A": 1.0,
            r"\omega": 1.0,
            r"\varphi": 0.0,
            r"u_0": 0.0
        }
        self._logger.info("CosineFunction initialized with params: %s", self._param)

    def get_formula(self) -> str:
        """Return a string representation of the function (for display)."""
        return r"u(t) = A \cdot \cos(\omega t + \varphi) + u_0"

    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized sine function using current parameters."""
        a = self._param[r"A"]
        omega = self._param[r"\omega"]
        varphi = self._param[r"\varphi"]
        u0 = self._param[r"u_0"]

        def u(t: np.ndarray) -> np.ndarray:
            return a * np.cos(omega * t + varphi) + u0

        return u


class Functions(Enum):
    UNIT_STEP = UnitStepFunction
    SINE = SineFunction
    COSINE = CosineFunction


class FunctionModel(QObject):
    """MVVM-style model holding function, input t, and output y.

    Attributes:
        functionChanged: Signal emitted when the function changes.
        parameterChanged: Signal emitted when the parameter changes.
        _selected_function: Current BaseFunction instance.
        _func_thread: Thread computing function outputs.
    """

    functionChanged = Signal()
    parameterChanged = Signal(str)

    def __init__(self, parent: QObject = None):
        """Initialize the FunctionModel.

        Args:
            dt: Time step for computations.
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        self._logger = logging.getLogger(f"Model.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FunctionModel initialized")

        self._selected_function: BaseFunction = UnitStepFunction()
        self._func_thread = None
        self._logger.info("Default function set: %s", type(self._selected_function).__name__)

    @Slot(Functions)
    def set_selected_function(self, function: Functions) -> None:
        """Change the current function by name.

        Args:
            function: Name of the function as string (matches Functions enum).
        """
        try:
            func_class = function.value
            if type(self._selected_function).__name__ != func_class.__name__:
                self._selected_function = func_class()
                self._logger.info("Function changed to: %s", type(self._selected_function).__name__)
                self.functionChanged.emit()
        except KeyError:
            self._logger.error("Function %s not found", function)

    def _get_selected_function(self) -> BaseFunction:
        """Getter for the function property."""
        return self._selected_function

    selected_function = Property(BaseFunction, _get_selected_function, notify=functionChanged)  # type: ignore[assignment]

    @Slot(str, float)
    def update_param_value(self, key: str, value: float) -> None:
        """
        Update the value of a function parameter if it has changed.

        Args:
            key (str): The name of the parameter to update.
            value (float): The new value to set.
        """
        # Get current parameter value
        current_value = self._selected_function.get_param_value(key)

        # Only update if the value actually changed
        if value != current_value:
            self._logger.info("Parameter '%s' changed from %f to %f", key, current_value, value)

            self._selected_function.update_param_value(key, value)

            # Notify observers that a parameter has changed
            self.parameterChanged.emit(key)
