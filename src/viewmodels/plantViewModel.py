from PySide6.QtCore import QObject, Signal, Property, Slot
import re

from utils import LatexRenderer
from .baseViewModel import BaseViewModel
from models import PlantModel
from services.controlsys import Plant

class PlantViewModel(BaseViewModel):

    numChanged = Signal()
    denChanged = Signal()
    isValidChanged = Signal()
    formulaChanged = Signal()

    def __init__(self, plant_modle: PlantModel, parent: QObject = None):

        super().__init__(parent)

        self._model = plant_modle

        self._default_formula = r"G(s) = \frac{b_q s^q + b_{q-1}s^{q-1} + \ldots + b_1 s + b_0}{a_n s^n + a_{n-1}s^{n-1} + \ldots + a_1 s + a_0}"
        self._last_formula = self._default_formula
        self._formula = self._default_formula

        self._num_input: str = ""
        self._den_input: str = ""

        self._connect_signals()


    def _connect_signals(self):
        # PlantModel
        self._model.numChanged.connect(self._on_model_num_changed)
        self._model.denChanged.connect(self._on_model_den_changed)
        self._model.isValidChanged.connect(self._on_model_is_valid_changed)

    # -------------------
    # num
    # -------------------
    def _on_model_num_changed(self):
        if not self.check_update_allowed("plant_num"):
            self._logger.debug("Blocked 'num' update (guard active)")
            return

        new_value = self._model.num
        self._logger.debug(f"Forwarding 'num' change from model (new_value={new_value})")

        self.numChanged.emit()

    def _get_num(self) -> str:
        self._logger.debug(f"Getter 'num' called (value={self._num_input})")
        return self._num_input

    @Slot(str)
    def update_num(self, value: str) -> None:
        self._logger.debug(f"update_num called (value={value})")

        if self._num_input == value:
            self._logger.debug("Skipped 'num' update (same string value)")
            return

        self._num_input = value
        self._logger.debug(f"Internal _num_input updated (value={self._num_input})")

        arr = self._str2array(value)

        if len(arr) == 0:
            self._logger.debug("Skipped 'num' update (string -> array conversion failed)")
            return

        if self._model.num == arr:
            self._logger.debug("Skipped 'num' update (model already has same array value)")
            return

        self._logger.debug(f"Updating model.num with {arr}")

        with self.updating("plant_num"):
            self._model.num = arr
            self._logger.debug("Emitting numChanged after model update")
            self._update_formula()
            self.numChanged.emit()

    num = Property(str, _get_num, notify=numChanged)  # type: ignore[assignment]

    # -------------------
    # den
    # -------------------
    def _on_model_den_changed(self):
        if not self.check_update_allowed("plant_den"):
            self._logger.debug("Blocked 'den' update (guard active)")
            return

        new_value = self._model.den
        self._logger.debug(f"Forwarding 'den' change from model (new_value={new_value})")

        self.denChanged.emit()

    def _get_den(self) -> str:
        self._logger.debug(f"Getter 'den' called (value={self._den_input})")
        return self._den_input

    @Slot(str)
    def update_den(self, value: str) -> None:
        self._logger.debug(f"update_den called (value={value})")

        if self._den_input == value:
            self._logger.debug("Skipped 'den' update (same string value)")
            return

        self._den_input = value
        self._logger.debug(f"Internal _den_input updated (value={self._den_input})")

        arr = self._str2array(value)

        if len(arr) == 0:
            self._logger.debug("Skipped 'den' update (string -> array conversion failed)")
            return

        if self._model.den == arr:
            self._logger.debug("Skipped 'den' update (model already has same array value)")
            return

        self._logger.debug(f"Updating model.den with {arr}")

        with self.updating("plant_den"):
            self._model.den = arr
            self._logger.debug("Emitting denChanged after model update")
            self._update_formula()
            self.denChanged.emit()

    den = Property(str, _get_den, notify=denChanged)  # type: ignore[assignment]

    # -------------------
    # is_valid
    # -------------------
    def _on_model_is_valid_changed(self):
        if not self.check_update_allowed("plant_is_valid"):
            self._logger.debug("Blocked 'is_valid' update (guard active)")
            return

        new_value = self._model.is_valid
        self._logger.debug(f"Forwarding 'is_valid' change from model (new_value={new_value})")
        self.isValidChanged.emit()

    def _get_is_valid(self) -> bool:
        return self._model.is_valid

    is_valid = Property(bool, _get_is_valid, notify=isValidChanged)  # type: ignore[assignment]

    # -------------------
    # formula
    # -------------------
    def get_formula(self) -> str:
        return self._formula

    def _update_formula(self) -> None:
        self._logger.debug("Updating formula...")

        if not self._model.is_valid:
            self._logger.debug("Model is not valid -> using last valid formula")
            self._formula = self._last_formula
            self.formulaChanged.emit()
            return

        try:
            self._logger.debug("Numerator raw: %s", self._model.num)
            self._logger.debug("Denominator raw: %s", self._model.den)

            num = LatexRenderer.array2polynom(self._model.num)
            den = LatexRenderer.array2polynom(self._model.den)

            self._formula = rf"G(s) = \frac{{{num}}}{{{den}}}"
            self._last_formula = self._formula

            self._logger.debug("Generated formula: %s", self._formula)

        except ValueError:
            self._logger.exception("Error while building formula")
            self._formula = self._last_formula

        self.formulaChanged.emit()

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

            self._logger.debug("Parsed '%s' -> %s", text, result)
            return result

        except ValueError:
            self._logger.debug("Cannot parse '%s'", text)
            return []