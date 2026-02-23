from PySide6.QtCore import QObject, Signal, QThread, Property, Slot, QTimer
import re
import numpy as np
import logging

from utils import LatexRenderer
from .baseViewModel import BaseViewModel
from models import PlantModel, SettingsModel, PsoConfigurationModel
from services.controlsys import Plant, MySolver

class StepResponseThread(QThread):
    """
    Background thread for computing the step response of a transfer function.

    This QThread performs the numerical simulation of a linear time-invariant
    (LTI) system defined by numerator and denominator coefficients. The
    computation is executed in a separate thread to prevent blocking the GUI.

    The thread stores the resulting time vector and output response internally
    and can emit signals when the computation starts and finishes.
    """

    def __init__(
        self,
        num: list[float],
        den: list[float],
        t0: float,
        t1: float,
        solver: MySolver,
    ):
        """
        Initialize the step response computation thread.

        Args:
            num (list[float]):
                Numerator coefficients of the transfer function
                (highest degree first).
            den (list[float]):
                Denominator coefficients of the transfer function
                (highest degree first).
            t0 (float):
                Start time of the simulation interval.
            t1 (float):
                End time of the simulation interval.
            solver (MySolver):
                Numerical solver used for integration.
        """
        super().__init__()
        self._num = num
        self._den = den
        self._t0 = t0
        self._t1 = t1
        self._solver = solver

        self._t: np.ndarray = np.array([])
        self._y: np.ndarray = np.array([])

        # Set up a logger for this worker
        self.logger = logging.getLogger(f"Thread.{self.__class__.__name__}")
        self.logger.debug("StepResponseThread initialized.")

    def run(self):
        """Executes the step response computation in a separate thread.

        Emits:
            started: When the computation starts.
            finished: When the computation ends.
        """
        self.logger.info("Step response computation started.")

        # Perform the step response calculation
        dt = (self._t1 - self._t0) / 5000
        plant = Plant(self._num, self._den)
        self._t, self._y = plant.step_response(self._t0, self._t1, dt, self._solver)

        self.logger.info("Step response computation finished.")

    def get_result(self) -> tuple[np.ndarray, np.ndarray]:
        return self._t, self._y

class PlantViewModel(BaseViewModel):

    numChanged = Signal()
    denChanged = Signal()
    isValidChanged = Signal()
    formulaChanged = Signal()
    stepResponseChanged = Signal()

    def __init__(
            self,
            model_plant: PlantModel,
            model_pso: PsoConfigurationModel,
            settings: SettingsModel,
            parent: QObject = None
    ):

        super().__init__(parent)

        self._model_plant = model_plant
        self._model_pso = model_pso
        self._settings = settings

        self._default_formula = r"G(s) = \frac{b_q s^q + b_{q-1}s^{q-1} + \ldots + b_1 s + b_0}{a_n s^n + a_{n-1}s^{n-1} + \ldots + a_1 s + a_0}"
        self._last_formula = self._default_formula
        self._formula = self._default_formula

        self._num_input: str = ""
        self._den_input: str = ""

        self._t: np.ndarray = np.array([])
        self._y: np.ndarray = np.array([])
        self._step_time: tuple[float, float] = (0, 10)
        self._thread = None

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
            self._logger.debug("Blocked 'num' update (guard active)")
            return

        new_value = self._model_plant.num
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

        if self._model_plant.num == arr:
            self._logger.debug("Skipped 'num' update (model already has same array value)")
            return

        self._logger.debug(f"Updating model.num with {arr}")

        with self.updating("plant_num"):
            self._model_plant.num = arr
            self._logger.debug("Emitting numChanged after model update")
            self._model_pso.num = arr
            self._logger.debug(f"PsoFunctionModel 'num' updated (num={arr})")
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

        new_value = self._model_plant.den
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

        if self._model_plant.den == arr:
            self._logger.debug("Skipped 'den' update (model already has same array value)")
            return

        self._logger.debug(f"Updating model.den with {arr}")

        with self.updating("plant_den"):
            self._model_plant.den = arr
            self._logger.debug("Emitting denChanged after model update")
            self._model_pso.den = arr
            self._logger.debug(f"PsoFunctionModel 'den' updated (num={arr})")
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

        new_value = self._model_plant.is_valid
        self._logger.debug(f"Forwarding 'is_valid' change from model (new_value={new_value})")
        self.isValidChanged.emit()

    def _get_is_valid(self) -> bool:
        return self._model_plant.is_valid

    is_valid = Property(bool, _get_is_valid, notify=isValidChanged)  # type: ignore[assignment]

    # -------------------
    # formula
    # -------------------
    def get_formula(self) -> str:
        return self._formula

    def _update_formula(self) -> None:
        self._logger.debug("Updating formula...")

        if not self._model_plant.is_valid:
            self._logger.debug("Model is not valid -> using last valid formula")
            self._formula = self._last_formula
            self.formulaChanged.emit()
            return

        try:
            self._logger.debug("Numerator raw: %s", self._model_plant.num)
            self._logger.debug("Denominator raw: %s", self._model_plant.den)

            num = LatexRenderer.array2polynom(self._model_plant.num)
            den = LatexRenderer.array2polynom(self._model_plant.den)

            self._formula = rf"G(s) = \frac{{{num}}}{{{den}}}"
            self._last_formula = self._formula

            self._logger.debug("Generated formula: %s", self._formula)

        except ValueError:
            self._logger.exception("Error while building formula")
            self._formula = self._last_formula

        self.formulaChanged.emit()

    # -------------------
    # step_response
    # -------------------
    def _compute_step_response_delayed(self) -> None:
        self.compute_step_response(*self._step_time)

    def _on_model_changed(self) -> None:
        if not self.check_update_allowed("plant_plant"):
            return

        # starte Timer neu bei jeder Eingabe
        self._recalc_timer.start(100)  # 100 ms warten

    @Slot(float, float)
    def compute_step_response(self, t0: float, t1: float) -> None:
        if self._thread is not None and self._thread.isRunning():
            return

        if not self._model_plant.is_valid:
            self._logger.debug("Model is invalid -> no (new) calculation")
            return

        # save step time
        self._step_time = (t0, t1)

        self._logger.debug(f"Computing step response for {t0} to {t1}")
        solver = self._settings.get_solver()
        self._thread = StepResponseThread(self._model_plant.num, self._model_plant.den, t0, t1, solver)

        self._thread.finished.connect(self._on_finished)

        self._thread.start()

    def _on_finished(self):
        self._t, self._y = self._thread.get_result()
        self._thread = None
        self.stepResponseChanged.emit()

    def get_step_response_result(self) -> tuple[np.ndarray, np.ndarray]:
        return self._t, self._y

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