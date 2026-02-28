import re

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
from numpy import ndarray

from models import ModelContainer, PlantModel, SettingsModel
from service import SimulationService
from utils import LatexRenderer
from .base_viewmodel import BaseViewModel


class PlantViewModel(BaseViewModel):

    numChanged = Signal()
    denChanged = Signal()
    isValidChanged = Signal()
    tfChanged = Signal()
    stepResponseChanged = Signal(ndarray, ndarray)

    def __init__(self, model_container: ModelContainer, simulation_service: SimulationService, parent: QObject = None):

        super().__init__(parent)

        self._model_plant: PlantModel = model_container.model_plant
        self._settings: SettingsModel = model_container.model_settings
        self._simulation_service = simulation_service

        self._default_tf = r"\frac{b_q s^q + b_{q-1}s^{q-1} + \ldots + b_1 s + b_0}{a_n s^n + a_{n-1}s^{n-1} + \ldots + a_1 s + a_0}"
        self._last_tf = self._default_tf
        self._tf = self._default_tf

        self._num_input: str = ""
        self._den_input: str = ""

        self._step_time: tuple[float, float] = (0, 10)

        self._recalc_timer = QTimer()
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.timeout.connect(self._compute_step_response_delayed)

        self._connect_signals()


    def _connect_signals(self):
        # PlantModel
        self._model_plant.numChanged.connect(self._on_model_num_changed)
        self._model_plant.denChanged.connect(self._on_model_den_changed)
        self._model_plant.isValidChanged.connect(self._on_model_is_valid_changed)
        self._model_plant.modelChanged.connect(self._on_model_changed)

    # -------------------
    # num
    # -------------------
    def _on_model_num_changed(self):
        if not self.check_update_allowed("plant_num"):
            self.logger.debug("Blocked 'num' update (guard active)")
            return

        new_value = self._model_plant.num
        self.logger.debug(f"Forwarding 'num' change from model (new_value={new_value})")

        self.numChanged.emit()

    def _get_num(self) -> str:
        self.logger.debug(f"Getter 'num' called (value={self._num_input})")
        return self._num_input

    @Slot(str)
    def update_num(self, value: str) -> None:
        self.logger.debug(f"update_num called (value={value})")

        if self._num_input == value:
            self.logger.debug("Skipped 'num' update (same string value)")
            return

        self._num_input = value
        self.logger.debug(f"Internal _num_input updated (value={self._num_input})")

        arr = self._str2array(value)

        if len(arr) == 0:
            self.logger.debug("Skipped 'num' update (string -> array conversion failed)")
            return

        if self._model_plant.num == arr:
            self.logger.debug("Skipped 'num' update (model already has same array value)")
            return

        self.logger.debug(f"Updating model.num with {arr}")

        with self.updating("plant_num"):
            self._model_plant.num = arr
            self.logger.debug("Emitting numChanged after model update")
            self._update_tf()
            self.numChanged.emit()

    num = Property(str, _get_num, notify=numChanged)  # type: ignore[assignment]

    # -------------------
    # den
    # -------------------
    def _on_model_den_changed(self):
        if not self.check_update_allowed("plant_den"):
            self.logger.debug("Blocked 'den' update (guard active)")
            return

        new_value = self._model_plant.den
        self.logger.debug(f"Forwarding 'den' change from model (new_value={new_value})")

        self.denChanged.emit()

    def _get_den(self) -> str:
        self.logger.debug(f"Getter 'den' called (value={self._den_input})")
        return self._den_input

    @Slot(str)
    def update_den(self, value: str) -> None:
        self.logger.debug(f"update_den called (value={value})")

        if self._den_input == value:
            self.logger.debug("Skipped 'den' update (same string value)")
            return

        self._den_input = value
        self.logger.debug(f"Internal _den_input updated (value={self._den_input})")

        arr = self._str2array(value)

        if len(arr) == 0:
            self.logger.debug("Skipped 'den' update (string -> array conversion failed)")
            return

        if self._model_plant.den == arr:
            self.logger.debug("Skipped 'den' update (model already has same array value)")
            return

        self.logger.debug(f"Updating model.den with {arr}")

        with self.updating("plant_den"):
            self._model_plant.den = arr
            self.logger.debug("Emitting denChanged after model update")
            self._update_tf()
            self.denChanged.emit()

    den = Property(str, _get_den, notify=denChanged)  # type: ignore[assignment]

    # -------------------
    # is_valid
    # -------------------
    def _on_model_is_valid_changed(self):
        if not self.check_update_allowed("plant_is_valid"):
            self.logger.debug("Blocked 'is_valid' update (guard active)")
            return

        new_value = self._model_plant.is_valid
        self.logger.debug(f"Forwarding 'is_valid' change from model (new_value={new_value})")
        self.isValidChanged.emit()

    def _get_is_valid(self) -> bool:
        return self._model_plant.is_valid

    is_valid = Property(bool, _get_is_valid, notify=isValidChanged)  # type: ignore[assignment]

    # -------------------
    # formula
    # -------------------
    def get_tf(self) -> str:
        return self._tf

    def _update_tf(self) -> None:
        self.logger.debug("Updating transfer function ...")

        if not self._model_plant.is_valid:
            self.logger.debug("Model is not valid -> using last valid transfer function")
            self._tf = self._last_tf
            self.tfChanged.emit()
            return

        try:
            self.logger.debug("Numerator raw: %s", self._model_plant.num)
            self.logger.debug("Denominator raw: %s", self._model_plant.den)

            num = LatexRenderer.array2polynom(self._model_plant.num)
            den = LatexRenderer.array2polynom(self._model_plant.den)

            self._tf = rf"\frac{{{num}}}{{{den}}}"
            self._last_tf = self._tf

            self.logger.debug("Generated transfer function: %s", self._tf)

        except ValueError:
            self.logger.exception("Error while building transfer function")
            self._tf = self._last_tf

        self.tfChanged.emit()

    # -------------------
    # step_response
    # -------------------
    def _on_model_changed(self) -> None:
        if not self.check_update_allowed("plant_plant"):
            return

        # starte Timer neu bei jeder Eingabe
        self._recalc_timer.start(100)  # 100 ms warten

    def _compute_step_response_delayed(self) -> None:
        self.compute_step_response(*self._step_time)

    @Slot(float, float)
    def compute_step_response(self, t0: float, t1: float) -> None:

        if not self._model_plant.is_valid:
            self.logger.debug("Model is invalid -> no (new) calculation")
            return

        # save step time
        self._step_time = (t0, t1)

        self.logger.debug(f"Computing step response for {t0} to {t1}")
        solver = self._settings.get_solver()
        self._simulation_service.compute_step_response(
            self._model_plant.num,
            self._model_plant.den,
            t0,
            t1,
            solver,
            self._on_result
        )

    def _on_result(self, t: ndarray, y: ndarray) -> None:
        self.stepResponseChanged.emit(t, y)

    # -------------------
    # Helper methods
    # -------------------
    def _str2array(self, text: str) -> list[float]:
        if not text.strip():
            return []

        try:
            # Trenner: Leerzeichen, Komma, Semikolon
            parts = re.split(r"[,\s;]+", text.strip())

            result = [float(p.replace(",", ".")) for p in parts if p]

            self.logger.debug("Parsed '%s' -> %s", text, result)
            return result

        except ValueError:
            self.logger.debug("Cannot parse '%s'", text)
            return []