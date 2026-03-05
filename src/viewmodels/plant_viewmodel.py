import re

from PySide6.QtCore import QObject, Signal, Slot, QTimer
import numpy as np
from numpy import ndarray

from app_domain.engine.types import PlantResponseContext
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

        self._last_tf = self._model_plant.tf

        self._num_input: str = ""
        self._den_input: str = ""

        self._step_time: tuple[float, float] = (0, 10)

        self._recalc_timer = QTimer()
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.timeout.connect(self._compute_step_response_delayed)

        self._connect_signals()

    def _connect_signals(self) -> None:
        # No model signals to connect (passive model)
        ...

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
        was_valid = self._model_plant.is_valid

        with self.updating("plant_num"):
            self._model_plant.num = arr
            is_valid = self._model_plant.is_valid

            if is_valid != was_valid:
                self.logger.debug(f"Emitting isValidChanged after num update ({was_valid} -> {is_valid})")
                self.isValidChanged.emit()

            if is_valid:
                self._on_model_changed()

            self.logger.debug("Emitting numChanged after model update")
            self._update_tf()
            self.numChanged.emit()

    num = BaseViewModel._logged_property(
        attribute="_num_input",
        notify_signal="numChanged",
        property_type=str,
        read_only=True,
    )

    # -------------------
    # den
    # -------------------
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
        was_valid = self._model_plant.is_valid

        with self.updating("plant_den"):
            self._model_plant.den = arr
            is_valid = self._model_plant.is_valid

            if is_valid != was_valid:
                self.logger.debug(f"Emitting isValidChanged after den update ({was_valid} -> {is_valid})")
                self.isValidChanged.emit()

            if is_valid:
                self._on_model_changed()

            self.logger.debug("Emitting denChanged after model update")
            self._update_tf()
            self.denChanged.emit()

    den = BaseViewModel._logged_property(
        attribute="_den_input",
        notify_signal="denChanged",
        property_type=str,
        read_only=True,
    )

    # -------------------
    # is_valid
    # -------------------
    is_valid = BaseViewModel._logged_property(
        attribute="_model_plant.is_valid",
        notify_signal="isValidChanged",
        property_type=bool,
        read_only=True,
    )

    # -------------------
    # formula
    # -------------------
    def get_tf(self) -> str:
        return self._model_plant.tf

    def _update_tf(self) -> None:
        self.logger.debug("Updating transfer function ...")

        if not self._model_plant.is_valid:
            self.logger.debug("Model is not valid -> using last valid transfer function")
            self._model_plant.tf = self._last_tf
            self.tfChanged.emit()
            return

        try:
            self.logger.debug(f"Numerator raw: {self._model_plant.num}")
            self.logger.debug(f"Denominator raw: {self._model_plant.den}")

            num = LatexRenderer.array2polynom(self._model_plant.num)
            den = LatexRenderer.array2polynom(self._model_plant.den)

            self._model_plant.tf = rf"\frac{{{num}}}{{{den}}}"
            self._last_tf = self._model_plant.tf

            self.logger.debug(f"Generated transfer function: {self._model_plant.tf}")

        except ValueError:
            self.logger.exception("Error while building transfer function")
            self._model_plant.tf = self._last_tf

        self.tfChanged.emit()

    # -------------------
    # step_response
    # -------------------
    def _on_model_changed(self) -> None:
        if not self.check_update_allowed("plant_plant"):
            return

        # Restart debounce timer after each input change.
        self._recalc_timer.start(100)  # wait 100 ms

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
        context = PlantResponseContext(
            num=self._model_plant.num,
            den=self._model_plant.den,
            t0=t0,
            t1=t1,
            solver=solver,
            reference=lambda t: np.where(t >= 0, 1.0, 0.0),
        )
        self._simulation_service.compute_plant_response(context, self._on_result)

    def _on_result(self, t: ndarray, y: ndarray) -> None:
        self.stepResponseChanged.emit(t, y)

    # -------------------
    # Helper methods
    # -------------------
    def _str2array(self, text: str) -> list[float]:
        if not text.strip():
            return []

        try:
            # Separators: whitespace, comma, semicolon.
            parts = re.split(r"[,\s;]+", text.strip())

            result = [float(p.replace(",", ".")) for p in parts if p]

            self.logger.debug(f"Parsed '{text}' -> {result}")
            return result

        except ValueError:
            self.logger.debug(f"Cannot parse '{text}'")
            return []
