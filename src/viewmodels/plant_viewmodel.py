from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
from numpy import ndarray
from sympy import SympifyError

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from app_types import PlantResponseContext, PlantField, ValidationResult
from utils import LoggedProperty, str2array, expr2array, array2expr, expr2latex, array2latex
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from service import SimulationService
    from models import ModelContainer, PlantModel, SettingsModel


class PlantViewModel(BaseViewModel):

    numChanged = Signal()
    denChanged = Signal()
    zeroChanged = Signal()
    poleChanged = Signal()
    isValidChanged = Signal()
    polyTfChanged = Signal()
    binomTfChanged = Signal()
    stepResponseChanged = Signal(ndarray, ndarray)

    def __init__(self, model_container: ModelContainer, simulation_service: SimulationService, parent: QObject = None):

        super().__init__(parent)

        self._model_plant: PlantModel = model_container.model_plant
        self._settings: SettingsModel = model_container.model_settings
        self._simulation_service = simulation_service

        self._last_tf_poly = self._model_plant.tf_poly
        self._last_tf_binom = self._model_plant.tf_binom

        self._active_tf_tab: int = 0

        self._was_valid: bool = False

        self._num_input: str = ""
        self._den_input: str = ""

        self._zero_input: str = ""
        self._pole_input: str = ""

        self._step_time: tuple[float, float] = (0, 10)

        self._recalc_timer = QTimer()
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.timeout.connect(self._compute_step_response_delayed)

    # -------------------
    # num
    # -------------------
    @Slot(str)
    def update_num(self, value: str) -> None:
        self.logger.debug(f"update_num called (value={value})")

        if self._num_input == value:
            self.logger.debug("Skipped 'num' update (same string value)")
            return

        self._num_input = value
        self.logger.debug(f"Internal _num_input updated (value={self._num_input})")

        arr = str2array(value)

        if len(arr) == 0:
            self._verify(
                PlantField.NUM,
                self._validate_non_empty_array(
                    arr=arr,
                    message=self.tr("Invalid numerator: enter at least one numeric coefficient."),
                ),
            )
            self.logger.debug("Skipped 'num' update (string -> array conversion failed)")
            return

        if not self._validate_poly_candidate(num=arr, den=self._model_plant.den, field=PlantField.NUM):
            self.logger.debug("Skipped 'num' update (num/den relation validation failed)")
            return

        if self._model_plant.num == arr:
            self.logger.debug("Skipped 'num' update (model already has same array value)")
            return

        self.logger.debug(f"Updating model.num with {arr}")

        with self.updating("plant_num"):
            self._model_plant.num = arr
            self._validate_model()

            self._update_transfer_functions()
            self.numChanged.emit()

            self._sync_poly_with_binom("num", "zero")

    num = LoggedProperty(
        path="_num_input",
        signal="numChanged",
        typ=str,
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

        arr = str2array(value)

        if len(arr) == 0:
            self._verify(
                PlantField.DEN,
                self._validate_non_empty_array(
                    arr=arr,
                    message=self.tr("Invalid denominator: enter at least one numeric coefficient."),
                ),
            )
            self.logger.debug("Skipped 'den' update (string -> array conversion failed)")
            return

        if not self._validate_poly_candidate(num=self._model_plant.num, den=arr, field=PlantField.DEN):
            self.logger.debug("Skipped 'den' update (num/den relation validation failed)")
            return

        if self._model_plant.den == arr:
            self.logger.debug("Skipped 'den' update (model already has same array value)")
            return

        self.logger.debug(f"Updating model.den with {arr}")

        with self.updating("plant_den"):
            self._model_plant.den = arr
            self._validate_model()

            self._update_transfer_functions()
            self.denChanged.emit()

            self._sync_poly_with_binom("den", "pole")

    den = LoggedProperty(
        path="_den_input",
        signal="denChanged",
        typ=str,
        read_only=True,
    )

    @Slot(str)
    def update_zero(self, value: str) -> None:
        self.logger.debug(f"update_zero called (value={value})")

        if self._zero_input == value:
            self.logger.debug("Skipped 'zero' update (same string value)")
            return

        self._zero_input = value
        self.logger.debug(f"Internal _zero_input updated (value={self._zero_input})")

        try:
            arr = expr2array(value)

            if self._model_plant.num == arr:
                self.logger.debug("Skipped 'zero' update (model already has same array value)")
                return

            with self.updating("plant_zero"):
                self._model_plant.num = arr
                self._validate_model()

                self._update_transfer_functions()
                self.zeroChanged.emit()

                self._sync_poly_with_binom("num", "zero")

        except (SympifyError, AttributeError, TypeError):
            self._verify(
                PlantField.ZERO,
                ValidationResult(False, message=self.tr("Invalid expression: enter a valid expression."))
            )


    zero = LoggedProperty(
        path="_zero_input",
        signal="zeroChanged",
        typ=str,
        read_only=True,
    )

    @Slot(str)
    def update_pole(self, value: str) -> None:
        self.logger.debug(f"update_pole called (value={value})")

        if self._pole_input == value:
            self.logger.debug("Skipped 'pole' update (same string value)")
            return

        self._pole_input = value
        self.logger.debug(f"Internal _pole_input updated (value={self._pole_input})")

        try:
            arr = expr2array(value)

            if self._model_plant.den == arr:
                self.logger.debug("Skipped 'pole' update (model already has same array value)")
                return

            with self.updating("plant_pole"):
                self._model_plant.den = arr
                self._validate_model()

                self._update_transfer_functions()
                self.poleChanged.emit()

                self._sync_poly_with_binom("den", "pole")

        except (SympifyError, AttributeError, TypeError):
            self._verify(
                PlantField.POLE,
                ValidationResult(False, message=self.tr("Invalid expression: enter a valid expression."))
            )


    pole = LoggedProperty(
        path="_pole_input",
        signal="poleChanged",
        typ=str,
        read_only=True,
    )

    # -------------------
    # is_valid
    # -------------------
    is_valid = LoggedProperty(
        path="_model_plant.is_valid",
        signal="isValidChanged",
        typ=bool,
        read_only=True,
    )

    # -------------------
    # formula
    # -------------------
    def get_poly_tf(self) -> str:
        return self._model_plant.tf_poly

    def get_binom_tf(self) -> str:
        return self._model_plant.tf_binom

    def get_current_tf(self) -> str:
        return self._model_plant.tf

    @Slot(int)
    def update_tf_tab(self, index: int) -> None:
        if self._active_tf_tab == index:
            return
        self._active_tf_tab = index
        self._sync_current_tf()
        self.polyTfChanged.emit()
        self.binomTfChanged.emit()

    def _update_poly_tf(self) -> None:
        self.logger.debug("Updating polynomial transfer function ...")

        if not self._model_plant.is_valid:
            self.logger.debug("Model is not valid -> using last valid polynomial transfer function")
            self._model_plant.tf_poly = self._last_tf_poly
            return

        try:
            self.logger.debug(f"Numerator raw: {self._model_plant.num}")
            self.logger.debug(f"Denominator raw: {self._model_plant.den}")

            num = array2latex(self._model_plant.num)
            den = array2latex(self._model_plant.den)

            self._model_plant.tf_poly = rf"\frac{{{num}}}{{{den}}}"
            self._last_tf_poly = self._model_plant.tf_poly

            self.logger.debug(f"Generated transfer function (poly): {self._model_plant.tf_poly}")

        except ValueError:
            self.logger.exception("Error while building transfer function")
            self._model_plant.tf_poly = self._last_tf_poly

    def _update_binom_tf(self) -> None:
        self.logger.debug("Updating binomial transfer function ...")

        if not self._model_plant.is_valid:
            self.logger.debug("Model is not valid -> using last valid binomial transfer function")
            self._model_plant.tf_binom = self._last_tf_binom
            return

        try:
            num_expr = array2expr(self._model_plant.num)
            den_expr = array2expr(self._model_plant.den)

            num = expr2latex(num_expr)
            den = expr2latex(den_expr)

            self._model_plant.tf_binom = rf"\frac{{{num}}}{{{den}}}"
            self._last_tf_binom = self._model_plant.tf_binom

            self.logger.debug(f"Generated transfer function (binom): {self._model_plant.tf_binom}")

        except Exception:
            self.logger.exception("Error while building binomial transfer function")
            self._model_plant.tf_binom = self._last_tf_binom

    def _update_transfer_functions(self) -> None:
        self._update_poly_tf()
        self._update_binom_tf()
        self._sync_current_tf()
        self.polyTfChanged.emit()
        self.binomTfChanged.emit()

    def _sync_current_tf(self) -> None:
        if self._active_tf_tab == 1:
            self._model_plant.tf = self._model_plant.tf_binom
        else:
            self._model_plant.tf = self._model_plant.tf_poly

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
        # save step time
        self._step_time = (t0, t1)

        if not self._model_plant.is_valid:
            self.logger.debug("Model is invalid -> no (new) calculation")
            return

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
    def _validate_model(self) -> None:

        is_valid = self._model_plant.is_valid

        if is_valid != self._was_valid:
            self.logger.debug(f"Emitting isValidChanged after den update ({self._was_valid} -> {is_valid})")
            self.isValidChanged.emit()

        if is_valid:
            self._on_model_changed()

        self._was_valid = is_valid

    @staticmethod
    def _validate_non_empty_array(*, arr: list[float], message: str) -> ValidationResult:
        if len(arr) == 0:
            return ValidationResult(False, message)
        return ValidationResult(True)

    def _validate_poly_candidate(self, *, num: list[float], den: list[float], field: PlantField) -> bool:
        if len(num) == 0 or len(den) == 0:
            return True

        if num[0] == 0:
            return self._verify(
                field,
                ValidationResult(False, self.tr("Invalid numerator: first coefficient must be non-zero.")),
            )

        if den[0] == 0:
            return self._verify(
                field,
                ValidationResult(False, self.tr("Invalid denominator: first coefficient must be non-zero.")),
            )

        return self._verify(
            field,
            self._validate_relation(
                value=len(num),
                other=len(den),
                relation="<=",
                message=self.tr(
                    "Invalid transfer function: denominator order must be greater than or equal to numerator order."
                ),
            ),
        )

    def _sync_poly_with_binom(self, poly_attr: str, binom_attr: str) -> None:
        """sync the polynom representation with binomial representation of the plant"""

        # check witch attribute has called the methode -> sync the oter attribute
        # poly to binom
        if not self.check_update_allowed(f"plant_{poly_attr}"):
            arr = str2array(getattr(self, f"_{poly_attr}_input"))
            expr = array2expr(arr)

            setattr(self, f"_{binom_attr}_input", expr)
            getattr(self, f"{binom_attr}Changed").emit()

        if not self.check_update_allowed(f"plant_{binom_attr}"):
            try:
                arr = expr2array(getattr(self, f"_{binom_attr}_input"))

                arr_str = f"{arr}".replace(",", "").replace("[", "").replace("]", "")

                setattr(self, f"_{poly_attr}_input", arr_str)
                getattr(self, f"{poly_attr}Changed").emit()

            except SympifyError:
                self.logger.warning("Error while building poly representation")

    @Slot()
    def refresh_from_model(self) -> None:
        self._num_input = " ".join(str(value) for value in self._model_plant.num)
        self._den_input = " ".join(str(value) for value in self._model_plant.den)

        try:
            self._zero_input = array2expr(self._model_plant.num) if self._model_plant.num else ""
        except (SympifyError, AttributeError, TypeError):
            self._zero_input = ""

        try:
            self._pole_input = array2expr(self._model_plant.den) if self._model_plant.den else ""
        except (SympifyError, AttributeError, TypeError):
            self._pole_input = ""

        self._update_transfer_functions()
        self._was_valid = self._model_plant.is_valid

        self.numChanged.emit()
        self.denChanged.emit()
        self.zeroChanged.emit()
        self.poleChanged.emit()
        self.isValidChanged.emit()

        if self._model_plant.is_valid:
            self.compute_step_response(*self._step_time)
