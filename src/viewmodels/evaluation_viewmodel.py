from PySide6.QtCore import QObject, Signal

from models import EvaluationModel
from .base_viewmodel import BaseViewModel
from .pso_configuration_viewmodel import PsoConfigurationViewModel


class EvaluationViewModel(BaseViewModel):
    """Exposes controller evaluation values and keeps them synced with PSO output."""
    kpChanged = Signal()
    tiChanged = Signal()
    tdChanged = Signal()
    tfChanged = Signal()

    def __init__(self, model_evaluator: EvaluationModel, vm_pso: PsoConfigurationViewModel,
                 parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_evaluator = model_evaluator
        self._vm_pso = vm_pso

        self._connect_signals()

    def _connect_signals(self) -> None:
        # Pull fresh evaluation values whenever a new PSO run completes.
        self._vm_pso.psoSimulationFinished.connect(self._on_pso_simulation_finished)

    kp: float = BaseViewModel._logged_property(
        attribute="_model_evaluator.kp",
        notify_signal="kpChanged",
        property_type=float
    )

    ti: float = BaseViewModel._logged_property(
        attribute="_model_evaluator.ti",
        notify_signal="tiChanged",
        property_type=float
    )

    td: float = BaseViewModel._logged_property(
        attribute="_model_evaluator.td",
        notify_signal="tdChanged",
        property_type=float
    )

    tf: float = BaseViewModel._logged_property(
        attribute="_model_evaluator.tf",
        notify_signal="tfChanged",
        property_type=float
    )

    def _on_pso_simulation_finished(self) -> None:
        result = self._vm_pso.get_pso_result()

        if result is None:
            # Clear previously shown gains if the run did not produce a valid result.
            self.kp = 0.0
            self.ti = 0.0
            self.td = 0.0
            self.tf = 0.0

            return

        self.kp = result.kp
        self.ti = result.ti
        self.td = result.td
        self.tf = result.tf
