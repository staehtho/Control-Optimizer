from PySide6.QtCore import QObject, Signal, Slot
from numpy import ndarray

from service import SimulationService
from app_domain.engine import ClosedLoopResponseContext
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import NullFunction
from models import (
    ModelContainer,
    SettingsModel,
    PlantModel,
    FunctionModel,
    ControllerModel,
    EvaluationModel,
)
from .base_viewmodel import BaseViewModel
from .pso_configuration_viewmodel import PsoConfigurationViewModel


class EvaluationViewModel(BaseViewModel):
    """Exposes controller evaluation values and keeps them synced with PSO output."""
    startTimeChanged = Signal()
    endTimeChanged = Signal()
    kpChanged = Signal()
    tiChanged = Signal()
    tdChanged = Signal()
    tfChanged = Signal()
    psoSimulationFinished = Signal(ExcitationTarget)
    closedLoopResponseChanged = Signal(ndarray, ndarray)

    def __init__(
            self,
            model_container: ModelContainer,
            vm_pso: PsoConfigurationViewModel,
            simulation_service: SimulationService,
            parent: QObject = None
    ) -> None:
        super().__init__(parent)

        self._model_plant: PlantModel = model_container.model_plant
        self._model_functions: dict[str, FunctionModel] = {
            i.name: model_container.ensure_function_model(i.name) for i in ExcitationTarget
        }
        self._model_controller: ControllerModel = model_container.model_controller
        self._settings: SettingsModel = model_container.model_settings
        self._model_evaluator: EvaluationModel = model_container.model_evaluator

        self._vm_pso = vm_pso
        self._simulation_service = simulation_service

        self._connect_signals()

    def _connect_signals(self) -> None:
        # Pull fresh evaluation values whenever a new PSO run completes.
        self._vm_pso.psoSimulationFinished.connect(self._on_pso_simulation_finished)

    # -------------------
    # simulation time window
    # -------------------
    def _verify_start_time(self, value: float) -> bool:
        if self._model_evaluator.end_time <= value:
            self.logger.debug(
                f"Skipped 'start_time' update (value={value} >= end_time={self._model_evaluator.end_time})"
            )
            return False
        return True

    start_time: float = BaseViewModel._logged_property(
        attribute="_model_evaluator.start_time",
        notify_signal="startTimeChanged",
        property_type=float,
        custom_setter=_verify_start_time,
    )

    def _verify_end_time(self, value: float) -> bool:
        if self._model_evaluator.start_time >= value:
            self.logger.debug(
                f"Skipped 'end_time' update (value={value} <= start_time={self._model_evaluator.start_time})"
            )
            return False
        return True

    end_time: float = BaseViewModel._logged_property(
        attribute="_model_evaluator.end_time",
        notify_signal="endTimeChanged",
        property_type=float,
        custom_setter=_verify_end_time,
    )

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

        # Persist simulation time window for pull-based views.
        # Prefer the result payload because tests/mocks may not expose VM fields.
        if result is not None:
            self.end_time = result.t1
            self.start_time = result.t0
        else:
            pso_start = getattr(self._vm_pso, "start_time", None)
            pso_end = getattr(self._vm_pso, "end_time", None)
            if isinstance(pso_start, (int, float)) and isinstance(pso_end, (int, float)) and pso_start < pso_end:
                self.end_time = float(pso_end)
                self.start_time = float(pso_start)

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

        # reset the functions to NullFunction
        for model in self._model_functions.values():
            model.selected_function = NullFunction()

        function_model = self._model_functions.get(result.excitation_target.name)
        if function_model is not None:
            function_model.selected_function = result.function.copy()

        self.psoSimulationFinished.emit(result.excitation_target)

    def get_simulation_time_window(self) -> tuple[float, float]:
        """Return the current simulation time window from evaluation model state."""
        return self.start_time, self.end_time


    @Slot(float, float)
    def compute_closed_loop_response(self, t0: float, t1: float) -> None:
        self.logger.debug("Running closed loop response.")

        context = ClosedLoopResponseContext(
            num=self._model_plant.num,
            den=self._model_plant.den,
            kp=self.kp,
            ti=self.ti,
            td=self.td,
            tf=self.tf,
            t0=t0,
            t1=t1,
            solver=self._settings.get_solver(),
            anti_windup=self._model_controller.anti_windup,
            constraint=(
                self._model_controller.constraint_min,
                self._model_controller.constraint_max,
            ),
            reference=self._model_functions.get(
                ExcitationTarget.REFERENCE.name).selected_function.get_function(),
            input_disturbance=self._model_functions.get(
                ExcitationTarget.INPUT_DISTURBANCE.name).selected_function.get_function(),
            measurement_disturbance=self._model_functions.get(
                ExcitationTarget.MEASUREMENT_DISTURBANCE.name).selected_function.get_function()
        )

        self._simulation_service.compute_closed_loop_response(context, self._on_compute_finished)

    def _on_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self.closedLoopResponseChanged.emit(t, y)
