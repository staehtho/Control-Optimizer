import sys

import numpy as np
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer

from app_domain.functions import BaseFunction, FunctionTypes
from models import FunctionModel
from service import SimulationService
from .base_viewmodel import BaseViewModel


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
        # FunctionModel
        self._model_function.functionChanged.connect(self._on_model_function_changed)
        self._model_function.parameterChanged.connect(self._on_model_parameter_changed)

    # -------------------
    # function
    # -------------------
    def _on_model_function_changed(self) -> None:
        if not self.check_update_allowed("function_function"):
            self._logger.debug("Blocked 'function' update (guard active)")
            return

        new_value = self._model_function.selected_function
        self._logger.debug(f"Forwarding 'function' change from model (new_type={type(new_value).__name__})")

        self.functionChanged.emit()

    @Slot(FunctionTypes)
    def set_selected_function(self, function: FunctionTypes) -> None:
        self._logger.debug(f"set_function called (function={function})")

        with self.updating("function_function"):
            self._model_function.set_selected_function(function)
            self._logger.debug("Emitting functionChanged after model update")
            self.functionChanged.emit()

    def _get_selected_function(self) -> BaseFunction:
        self._logger.debug(f"Getter 'function' called (type={type(self._model_function.selected_function).__name__})")
        return self._model_function.selected_function


    selected_function = Property(BaseFunction, _get_selected_function, notify=functionChanged)  # type: ignore[assignment]

    def _compute_function_delayed(self) -> None:
        self.compute_function(*self._function_time)

    @Slot(float, float)
    def compute_function(self, t0:float, t1: float) -> None:
        """Start computing the function output vector y(t) asynchronously."""

        if self._model_function.selected_function is None:
            self._logger.warning("Computation not started, ignoring request")
            return

        # Avoid t0 being exactly zero for numerical reasons
        if t0 == 0:
            t0 = -sys.float_info.min
        t = np.linspace(t0, t1, 5000)

        # save step time
        self._function_time = (t0, t1)

        self._logger.debug(f"Computing function (type={type(self._model_function.selected_function).__name__}) for {t0} to {t1}")
        func = self._model_function.selected_function.get_function()
        self._simulation_service.compute_function(t, func, self._on_result)

    def _on_result(self, t: np.ndarray, y: np.ndarray) -> None:
        self.computeFinished.emit(t, y)

    # -------------------
    # param
    # -------------------
    def _on_model_parameter_changed(self, key: str):
        if not self.check_update_allowed("function_param"):
            self._logger.debug("Blocked 'parameter' update (guard active)")
            return

        new_value = self._model_function.selected_function.get_param_value(key)
        self._logger.debug(f"Forwarding 'parameter' change from model ({key=}={new_value=})")

        # starte Timer neu bei jeder Eingabe
        self._recalc_timer.start(100)  # 100 ms warten

        self.parameterChanged.emit(key)

    @Slot(str, float)
    def update_param_value(self, key: str, value: float) -> None:
        self._logger.debug(f"update_param_value called ({key=}, {value=})")

        old_value = self._model_function.selected_function.get_param_value(key)
        if value != old_value:
            with self.updating("function_param"):
                self._model_function.update_param_value(key, value)
                self._logger.info("Parameter '%s' updated from %f to %f", key, old_value, value)
                self.parameterChanged.emit(key)
