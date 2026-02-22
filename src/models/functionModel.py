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
        self._label: object = None
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

    def get_label(self) -> object:
        """Return the label of the function."""
        return self._label

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

    def __init__(self) -> None:
        """Initialize unit step function."""
        super().__init__()
        self._label = QT_TRANSLATE_NOOP("FunctionModel", "Unit step function")
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

    def __init__(self) -> None:
        """Initialize sine function with default parameters."""
        super().__init__()
        self._param: dict[str, float] = {
            r"A": 1.0,
            r"\omega": 1.0,
            r"\varphi": 0.0,
            r"u_0": 0.0
        }
        self._label = QT_TRANSLATE_NOOP("FunctionModel", "Sine function")
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


class Functions(Enum):
    UNIT_STEP = UnitStepFunction
    SINE = SineFunction


class FunctionModel(QObject):
    """MVVM-style model holding function, input t, and output y.

    Attributes:
        functionChanged: Signal emitted when the function changes.
        computeFinished: Signal emitted when computation is complete.
        _selected_function: Current BaseFunction instance.
        _func_thread: Thread computing function outputs.
    """

    t0Changed = Signal()
    t1Changed = Signal()
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

        self._t0: float = 0.0
        self._t1: float = 1.0
        self._dt = dt
        self._selected_function: BaseFunction = UnitStepFunction()
        self._func_thread = None
        self._logger.info("Default function set: %s", type(self._selected_function).__name__)

    # -------------------
    # t0
    # -------------------
    def _get_t0(self) -> float:
        self._logger.debug(f"Getter 'num' called (value={self._t0})")
        return self._t0

    def _set_t0(self, value: float) -> None:
        self._logger.debug(f"Setter 't0' called (value={value})")
        if value == self._t0:
            self._logger.debug("Skipped 't0' update (same value)")
            return

        if value >= self._t1:
            self._logger.debug(f"Skipped 't0' update ({self._t0=} >= {self._t1=})")
            return

        self._t0 = value
        self._logger.debug("Emitting t0Changed after model update")
        self.t0Changed.emit()

    t0 = Property(float, _get_t0, _set_t0, notify=t0Changed)    # type: ignore[assignment]

    # -------------------
    # t1
    # -------------------
    def _get_t1(self) -> float:
        self._logger.debug(f"Getter 'num' called (value={self._t1})")
        return self._t1

    def _set_t1(self, value: float) -> None:
        self._logger.debug(f"Setter 't1' called (value={value})")
        if value == self._t1:
            self._logger.debug("Skipped 't1' update (same value)")
            return

        if value <= self._t0:
            self._logger.debug(f"Skipped 't1' update ({self._t1=} <= {self._t0=})")
            return

        self._t1 = value
        self._logger.debug("Emitting t1Changed after model update")
        self.t1Changed.emit()

    t1 = Property(float, _get_t1, _set_t1, notify=t1Changed)  # type: ignore[assignment]

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

    @Slot()
    def compute(self) -> None:
        """Start computing the function output vector y(t) asynchronously."""

        # Avoid starting a new thread if computation is already running
        if self._func_thread is not None and self._func_thread.isRunning():
            self._logger.warning("Computation already running, ignoring request")
            return

        # Avoid t0 being exactly zero for numerical reasons
        if self._t0 == 0:
            self._t0 = -sys.float_info.min
        t = np.arange(self._t0, self._t1 + self._dt, self._dt)

        self._logger.debug("Starting computation for t.size=%d", t.size)
        self._func_thread = FunctionComputeThread(t, self._selected_function.compute_function())
        self._func_thread.finished.connect(self._on_finished)
        self._func_thread.start()

    def _on_finished(self):
        """Slot called when computation thread finishes. Updates function t and y."""
        self._selected_function.t, self._selected_function.y = self._func_thread.get_result()
        self._logger.info("Computation finished. y.size=%d", self._selected_function.y.size)

        self._func_thread = None
        self.computeFinished.emit()