from PySide6.QtCore import QObject, QThread, Signal, Slot, Property
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
        self._logger.info("Computation finished")

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

    def __format__(self, format_spec: str) -> str:
        """Return a string representation of the function (for display)."""
        format_spec = format_spec.strip().lower()
        if format_spec == "display":
            raise NotImplementedError
        return super().__format__(format_spec)

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
    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a callable that computes y(t)."""
        ...


class UnitStepFunction(BaseFunction):
    """Unit step function u(t)."""

    def __init__(self) -> None:
        """Initialize unit step function."""
        super().__init__()
        self._logger.info("UnitStepFunction initialized")

    def __format__(self, format_spec: str) -> str:
        """Return a string representation of the function (for display)."""
        format_spec = format_spec.strip().lower()
        if format_spec == "display":
            return r"u = \sigma(t)"
        return super().__format__(format_spec)

    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized function computing the unit step."""
        def u(t: np.ndarray) -> np.ndarray:
            return np.where(t >= 0, 1.0, 0.0)
        return u


class SineFunction(BaseFunction):
    """Sine function u(t) = A*sin(ωt + φ) + y0."""

    def __init__(self) -> None:
        """Initialize sine function with default parameters."""
        super().__init__()
        self._param: dict[str, float] = {
            r"A": 1.0,
            r"\omega": 1.0,
            r"\varphi": 0.0,
            r"y_0": 0.0
        }
        self._logger.info("SineFunction initialized with params: %s", self._param)

    def __format__(self, format_spec: str) -> str:
        """Return a string representation of the function (for display)."""
        format_spec = format_spec.strip().lower()
        if format_spec == "display":
            return r"u = A \sin(\omega t + \varphi) + y_0"
        return super().__format__(format_spec)

    def compute_function(self) -> Callable[[np.ndarray], np.ndarray]:
        """Return a vectorized sine function using current parameters."""
        a = self._param[r"A"]
        omega = self._param[r"\omega"]
        varphi = self._param[r"\varphi"]
        y0 = self._param[r"y_0"]

        def u(t: np.ndarray) -> np.ndarray:
            return a * np.sin(omega * t + varphi) + y0

        return u


class Functions(Enum):
    """Enum mapping function names to their classes."""
    UNIT_STEP_FUNCTION = UnitStepFunction
    SINE_FUNCTION = SineFunction


class FunctionModel(QObject):
    """MVVM-style model holding function, input t, and output y.

    Attributes:
        functionChanged: Signal emitted when the function changes.
        computeFinished: Signal emitted when computation is complete.
        _function: Current BaseFunction instance.
        _func_thread: Thread computing function outputs.
    """

    functionChanged = Signal()
    computeFinished = Signal()

    def __init__(self, dt: float = 1e-4, parent: QObject = None):
        """Initialize the FunctionModel.

        Args:
            dt: Time step for computations.
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        self._logger = logging.getLogger(f"Model.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FunctionModel initialized")

        self._dt = dt
        self._function: BaseFunction = UnitStepFunction()
        self._func_thread = None
        self._logger.info("Default function set: %s", type(self._function).__name__)

    @Slot(str)
    def set_function(self, function: str) -> None:
        """Change the current function by name.

        Args:
            function: Name of the function as string (matches Functions enum).
        """
        try:
            func_class = Functions[function.upper()].value
            if type(self._function) != func_class:
                self._function = func_class()
                self._logger.info("Function changed to: %s", type(self._function).__name__)
                self.functionChanged.emit()
        except KeyError:
            self._logger.error("Function %s not found", function)

    def _get_function(self) -> BaseFunction:
        """Getter for the function property."""
        return self._function

    function = Property(BaseFunction, _get_function, notify=functionChanged)  # type: ignore[assignment]

    def compute(self, t0: float, t1: float) -> None:
        """Start computing the function output vector y(t) asynchronously.

        Args:
            t0: Start time.
            t1: End time.
        """
        # Avoid starting a new thread if computation is already running
        if self._func_thread is not None and self._func_thread.isRunning():
            self._logger.warning("Computation already running, ignoring request")
            return

        # Avoid t0 being exactly zero for numerical reasons
        if t0 == 0:
            t0 = -sys.float_info.min
        t = np.arange(t0, t1 + self._dt, self._dt)

        self._logger.debug("Starting computation for t.size=%d", t.size)
        self._func_thread = FunctionComputeThread(t, self._function.compute_function())
        self._func_thread.finished.connect(self._on_finished)
        self._func_thread.start()

    def _on_finished(self):
        """Slot called when computation thread finishes. Updates function t and y."""
        self._function.t, self._function.y = self._func_thread.get_result()
        self._logger.info("Computation finished. y.size=%d", self._function.y.size)

        self._func_thread = None
        self.computeFinished.emit()