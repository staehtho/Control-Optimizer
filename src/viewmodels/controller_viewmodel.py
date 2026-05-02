from __future__ import annotations
from typing import TYPE_CHECKING, Any
from PySide6.QtCore import QObject, Signal, Slot

from app_domain.controlsys import AntiWindup, ControllerType
from .base_viewmodel import BaseViewModel
from app_types import ControllerField, CONTROLLER_SPECS, ControllerSpec
from utils import LoggedProperty

if TYPE_CHECKING:
    from models import ControllerModel


class ControllerViewModel(BaseViewModel):
    controllerTypeChanged = Signal()
    antiWindupChanged = Signal()
    constraintMinChanged = Signal()
    constraintMaxChanged = Signal()
    kaChanged = Signal()
    kaEnabledChanged = Signal()
    tuningFactorChanged = Signal()
    samplingRateChanged = Signal()

    def __init__(self, model_controller: ControllerModel, parent: QObject = None):
        super().__init__(parent)

        self._model_controller = model_controller

    # ============================================================
    # controller
    # ============================================================
    def _custom_setter_controller_type(self, value: ControllerType) -> ControllerType:

        self._model_controller.controller_spec = CONTROLLER_SPECS[value]

        return value

    controller_type: ControllerType = LoggedProperty(
        path="_model_controller.controller_type",
        signal="controllerTypeChanged",
        typ=ControllerType,
        custom_setter=_custom_setter_controller_type
    )

    controller_spec: ControllerSpec = LoggedProperty(
        path="_model_controller.controller_spec",
        typ=ControllerSpec,
        read_only=True
    )

    # ============================================================
    # anti windup
    # ============================================================
    def _custom_setter_anti_windup(self, value: AntiWindup) -> bool:
        enabled = value == AntiWindup.BACKCALCULATION
        if enabled != self.ka_enabled:
            self.ka_enabled = enabled

        return True  # allow normal update

    anti_windup: AntiWindup = LoggedProperty(
        path="_model_controller.anti_windup",
        signal="antiWindupChanged",
        typ=AntiWindup,
        custom_setter=_custom_setter_anti_windup
    )

    # ============================================================
    # constraint
    # ============================================================
    def _verify_constraint_min(self, value: float):
        result = self._validate_relation(
            valid=value < self._model_controller.constraint_max,
            message=self.tr(
                "Invalid value: min ({value}) must be smaller than max ({max})."
            ).format(value=value, max=self._model_controller.constraint_max)
        )

        return self._verify(ControllerField.CONSTRAINT_MIN, result)

    constraint_min: float = LoggedProperty(
        path="_model_controller.constraint_min",
        signal="constraintMinChanged",
        typ=float,
        custom_setter=_verify_constraint_min
    )

    def _verify_constraint_max(self, value: float):
        result = self._validate_relation(
            valid=value > self._model_controller.constraint_min,
            message=self.tr(
                "Invalid value: max ({value}) must be greater than min ({min})."
            ).format(value=value, min=self._model_controller.constraint_min)
        )

        return self._verify(ControllerField.CONSTRAINT_MAX, result)

    constraint_max: float = LoggedProperty(
        path="_model_controller.constraint_max",
        signal="constraintMaxChanged",
        typ=float,
        custom_setter=_verify_constraint_max
    )

    # ============================================================
    # ka
    # ============================================================
    ka: float = LoggedProperty(
        path="_model_controller.ka",
        signal="kaChanged",
        typ=float,
    )

    ka_enabled: bool = LoggedProperty(
        path="_model_controller.ka_enabled",
        signal="kaEnabledChanged",
        typ=bool,
    )

    # ============================================================
    # filter time constant
    # ============================================================
    tuning_factor: float = LoggedProperty(
        path="_model_controller.tuning_factor",
        signal="tuningFactorChanged",
        typ=float,
    )

    def set_sampling_rate_text(self, **kwargs: Any) -> None:
        get_text = kwargs.get("get_text", lambda: "")
        text = get_text()
        if text.strip() == "":
            self.sampling_rate = ""
            return

        if not kwargs.get("commit", False):
            return

        self.sampling_rate = text

    def _custom_setter_sampling_rate(self, value: str) -> float | None | bool:
        text = value.strip()
        if text == "":
            new_value = None
        else:
            try:
                new_value = float(text)
            except ValueError:
                self.logger.warning(f"Invalid sampling rate input: {value!r}")
                return False

        return new_value

    sampling_rate: str = LoggedProperty(
        path="_model_controller.sampling_rate",
        signal="samplingRateChanged",
        typ=str,
        custom_setter=_custom_setter_sampling_rate
    )

    @Slot()
    def refresh_from_model(self) -> None:
        self.controllerTypeChanged.emit()
        self.antiWindupChanged.emit()
        self.constraintMinChanged.emit()
        self.constraintMaxChanged.emit()
        self.kaChanged.emit()
        self.kaEnabledChanged.emit()
        self.tuningFactorChanged.emit()
        self.samplingRateChanged.emit()
