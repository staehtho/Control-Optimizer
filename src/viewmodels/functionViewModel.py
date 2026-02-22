from PySide6.QtCore import QObject, Signal, Property, Slot

from models import FunctionModel, Functions, BaseFunction
from .baseViewModel import BaseViewModel

class FunctionViewModel(BaseViewModel):

    t0Changed = Signal()
    t1Changed = Signal()
    functionChanged = Signal()
    computeFinished = Signal()

    def __init__(self, model_function: FunctionModel, parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_function = model_function

        self._connect_signals()

    def _connect_signals(self) -> None:
        # FunctionModel
        self._model_function.t0Changed.connect(self._on_model_t0_changed)
        self._model_function.t1Changed.connect(self._on_model_t1_changed)
        self._model_function.functionChanged.connect(self._on_model_function_changed)
        self._model_function.computeFinished.connect(lambda: self.computeFinished.emit())

    # -------------------
    # t0
    # -------------------
    def _on_model_t0_changed(self) -> None:
        if not self.check_update_allowed("function_t0"):
            self._logger.debug("Blocked 't0' update (guard active)")
            return

        new_value = self._model_function.t0
        self._logger.debug(f"Forwarding 't0' change from model (new_value={new_value})")

        self.t0Changed.emit()

    def _get_t0(self) -> float:
        self._logger.debug(f"Getter 't0' called (value={self._model_function.t0})")
        return self._model_function.t0

    def _set_t0(self, value: float) -> None:
        self._logger.debug(f"Setter 't0' called (value={value})")
        if value != self._model_function.t0:
            with self.updating("function_t0"):
                self._model_function.t0 = value
                self._logger.debug("Emitting t0Changed after model update")
                self.t0Changed.emit()

    t0 = Property(float, _get_t0, _set_t0, notify=t0Changed)    # type: ignore[assignment]

    # -------------------
    # t1
    # -------------------
    def _on_model_t1_changed(self) -> None:
        if not self.check_update_allowed("function_t1"):
            self._logger.debug("Blocked 't1' update (guard active)")
            return

        new_value = self._model_function.t1
        self._logger.debug(f"Forwarding 't1' change from model (new_value={new_value})")

        self.t1Changed.emit()

    def _get_t1(self) -> float:
        self._logger.debug(f"Getter 't1' called (value={self._model_function.t1})")
        return self._model_function.t1

    def _set_t1(self, value: float) -> None:
        self._logger.debug(f"Setter 't1' called (value={value})")
        if value != self._model_function.t1:
            with self.updating("function_t1"):
                self._model_function.t1 = value
                self._logger.debug("Emitting t1Changed after model update")
                self.t1Changed.emit()

    t1 = Property(float, _get_t1, _set_t1, notify=t1Changed)  # type: ignore[assignment]

    # -------------------
    # function
    # -------------------
    def _on_model_function_changed(self) -> None:
        if not self.check_update_allowed("function_function"):
            self._logger.debug("Blocked 'function' update (guard active)")
            return

        new_value = self._model_function.function
        self._logger.debug(f"Forwarding 'function' change from model (new_type={type(new_value).__name__})")

        self.functionChanged.emit()

    @Slot(Functions)
    def set_function(self, function: Functions) -> None:
        self._logger.debug(f"set_function called (function={function})")

        with self.updating("function_function"):
            self._model_function.set_function(function)
            self._logger.debug("Emitting functionChanged after model update")
            self.functionChanged.emit()

    def _get_function(self) -> BaseFunction:
        self._logger.debug(f"Getter 'function' called (type={type(self._model_function.function).__name__})")
        return self._model_function.function


    function = Property(BaseFunction, _get_function, notify=functionChanged)  # type: ignore[assignment]

    @Slot()
    def compute_function(self) -> None:
        self._logger.debug(f"Computing function (type={type(self._model_function.function).__name__})")
        self._model_function.compute()

