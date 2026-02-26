from PySide6.QtCore import QObject, Signal


from app_domain.controlsys import AntiWindup
from models import ControllerModel
from .base_viewmodel import BaseViewModel


class ControllerViewModel(BaseViewModel):
    controllerTypeChanged = Signal()
    antiWindupChanged = Signal()
    constraintMinChanged = Signal()
    constraintMaxChanged = Signal()

    def __init__(self, model_controller: ControllerModel, parent: QObject = None):
        super().__init__(parent)

        self._model_controller = model_controller

        self._connect_signals()

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    # -------------------
    # controller
    # -------------------
    controller_type = BaseViewModel._logged_property(
        attribute="_model_controller.controller_type",
        notify_signal="controllerChanged",
        property_type=str
    )

    # -------------------
    # anti windup
    # -------------------
    anti_windup = BaseViewModel._logged_property(
        attribute="_model_controller.anti_windup",
        notify_signal="antiWindupChanged",
        property_type=AntiWindup
    )

    # -------------------
    # constraint
    # -------------------
    def _verify_constraint_min(self, value: float) -> bool:
        if self._model_controller.constraint_max <= value:
            self.logger.debug(
                f"Skipped 'constraint_min' update (value={value} >= constraint_min={self._model_controller.constraint_min})")
            return False
        return True

    constraint_min = BaseViewModel._logged_property(
        attribute="_model_controller.constraint_min",
        notify_signal="constraintMinChanged",
        property_type=float,
        custom_setter=_verify_constraint_min
    )

    def _verify_constraint_max(self, value: float) -> bool:
        if self._model_controller.constraint_min >= value:
            self.logger.debug(
                f"Skipped 'constraint_max' update (value={value} <= constraint_max={self._model_controller.constraint_max})")
            return False
        return True

    constraint_max = BaseViewModel._logged_property(
        attribute="_model_controller.constraint_max",
        notify_signal="constraintMaxChanged",
        property_type=float,
        custom_setter=_verify_constraint_max
    )