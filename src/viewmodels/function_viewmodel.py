import sys

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, QTimer

from app_domain.functions import BaseFunction, FunctionTypes
from models import FunctionModel
from service import SimulationService
from .base_viewmodel import BaseViewModel
from utils import LoggedProperty


class FunctionViewModel(BaseViewModel):

    functionChanged = Signal()
    computeFinished = Signal(np.ndarray, np.ndarray)
    parameterChanged = Signal(str)

    def __init__(self, model_function: FunctionModel, simulation_service: SimulationService, parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_function = model_function
        self._simulation_service = simulation_service

        self._function_time: tuple[float, float] = (0, 10)

        self._recalc_timer = QTimer()
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.timeout.connect(self._compute_function_delayed)

        self._connect_signals()

    def _connect_signals(self) -> None:
        # No model signals to connect (passive model)
        ...

    # -------------------
    # function
    # -------------------
    @Slot(FunctionTypes)
    def set_selected_function(self, function: FunctionTypes) -> None:
        self.logger.debug(f"set_function called (function={function})")

        func_class = function.value
        current_type = type(self._model_function.selected_function)
        if current_type is func_class:
            self.logger.debug("Skipped 'function' update (same type)")
            return

        with self.updating("function_function"):
            self._model_function.selected_function = func_class()
            self.logger.debug("Emitting functionChanged after model update")
            self.functionChanged.emit()

    selected_function = LoggedProperty(
        path="_model_function.selected_function",
        typ=BaseFunction,
        read_only=True,
    )

    def _compute_function_delayed(self) -> None:
        self.compute_function(*self._function_time)

    @Slot(float, float)
    def compute_function(self, t0:float, t1: float) -> None:
        """Start computing the function output vector y(t) asynchronously."""

        if self._model_function.selected_function is None:
            self.logger.warning("Computation not started, ignoring request")
            return

        # Avoid t0 being exactly zero for numerical reasons
        if t0 == 0:
            t0 = -sys.float_info.min
        t = np.linspace(t0, t1, 5000)

        # save step time
        self._function_time = (t0, t1)

        self.logger.debug(
            f"Computing function (type={type(self._model_function.selected_function).__name__}) for {t0} to {t1}")
        func = self._model_function.selected_function.get_function()
        self._simulation_service.compute_function(t, func, self._on_result)

    def _on_result(self, t: np.ndarray, y: np.ndarray) -> None:
        self.computeFinished.emit(t, y)

    @Slot()
    def refresh_from_model(self) -> None:
        """
        Notify bound views that the selected function instance in the model changed
        externally (e.g. by another ViewModel).
        """
        self.functionChanged.emit()

    # -------------------
    # param
    # -------------------
    @Slot(str, float)
    def update_param_value(self, key: str, value: float) -> None:
        self.logger.debug(f"update_param_value called ({key=}, {value=})")

        old_value = self._model_function.selected_function.get_param_value(key)
        if value != old_value:
            with self.updating("function_param"):
                self._model_function.selected_function.update_param_value(key, value)
                self.logger.info(f"Parameter '{key}' updated from {old_value:.6f} to {value:.6f}")
                self._recalc_timer.start(100)  # 100 ms wait before recompute
                self.parameterChanged.emit(key)
                self.functionChanged.emit()
