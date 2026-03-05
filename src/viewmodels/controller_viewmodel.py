from PySide6.QtCore import QObject, Signal

from app_domain.controlsys import AntiWindup
from models import ControllerModel
from .base_viewmodel import BaseViewModel
from utils import LoggedProperty


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
    controller_type = LoggedProperty(
        path="_model_controller.controller_type",
        signal="controllerTypeChanged",
        typ=str
    )

    # -------------------
    # anti windup
    # -------------------
    anti_windup = LoggedProperty(
        path="_model_controller.anti_windup",
        signal="antiWindupChanged",
        typ=AntiWindup
    )

    # -------------------
    # constraint
    # -------------------
    def _verify_constraint_min(self, value: float) -> bool:
        if self._model_controller.constraint_max <= value:
            self.logger.debug(
                f"Skipped 'constraint_min' update (value={value} >= constraint_max={self._model_controller.constraint_max})"
            )
            return False
        return True

    constraint_min = LoggedProperty(
        path="_model_controller.constraint_min",
        signal="constraintMinChanged",
        typ=float,
        custom_setter=_verify_constraint_min
    )

    def _verify_constraint_max(self, value: float) -> bool:
        if self._model_controller.constraint_min >= value:
            self.logger.debug(
                f"Skipped 'constraint_max' update (value={value} <= constraint_max={self._model_controller.constraint_max})"
            )
            return False
        return True

    constraint_max = LoggedProperty(
        path="_model_controller.constraint_max",
        signal="constraintMaxChanged",
        typ=float,
        custom_setter=_verify_constraint_max
    )
