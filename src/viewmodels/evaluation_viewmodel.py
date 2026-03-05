import sys

from PySide6.QtCore import QObject, Signal, Slot
from numpy import ndarray, linspace

from service import SimulationService
from app_domain.engine.types import PlantResponseContext, PsoResult
from app_domain.engine.types import ClosedLoopResponseContext
from app_domain.controlsys import ExcitationTarget
from app_domain.functions import NullFunction, BaseFunction
from models import SettingsModel, PsoSimulationSnapshot
from .base_viewmodel import BaseViewModel
from .pso_configuration_viewmodel import PsoConfigurationViewModel


class EvaluationViewModel(BaseViewModel):
    """Exposes controller evaluation values and keeps them synced with PSO output."""
    psoSimulationFinished = Signal()
    closedLoopResponseChanged = Signal(ndarray, ndarray, ndarray)
    plantResponseChanged = Signal(ndarray, ndarray)
    functionChanged = Signal(ndarray, ndarray)

    def __init__(
            self,
            settings: SettingsModel,
            vm_pso: PsoConfigurationViewModel,
            simulation_service: SimulationService,
            parent: QObject = None
    ) -> None:
        super().__init__(parent)

        self._settings = settings
        self._pos_result: PsoResult | None = None
        self._pso_snapshot: PsoSimulationSnapshot | None = None

        self._vm_pso = vm_pso
        self._simulation_service = simulation_service

        self._connect_signals()

    def _connect_signals(self) -> None:
        # Pull fresh evaluation values whenever a new PSO run completes.
        self._vm_pso.psoSimulationFinished.connect(self._on_pso_simulation_finished)

    t0 = BaseViewModel._logged_property(
        attribute="_pos_result.t0",
        property_type=float,
        read_only=True
    )

    t1 = BaseViewModel._logged_property(
        attribute="_pos_result.t1",
        property_type=float,
        read_only=True
    )

    plant_tf = BaseViewModel._logged_property(
        attribute="_pso_snapshot.plant_tf",
        property_type=str,
        read_only=True
    )

    excitation_target = BaseViewModel._logged_property(
        attribute="_pso_snapshot.excitation_target",
        property_type=ExcitationTarget,
        read_only=True
    )

    def _on_pso_simulation_finished(self) -> None:
        self._pos_result = self._vm_pso.get_pso_result()
        self._pso_snapshot = self._vm_pso.get_pso_snapshot()

        self.psoSimulationFinished.emit()


    @Slot(float, float)
    def compute_closed_loop_response(self, t0: float, t1: float) -> None:
        if self._pos_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, closed loop response are not computed")
            return

        self.logger.debug("Running closed loop response.")

        function: dict[ExcitationTarget, BaseFunction] = {target: NullFunction() for target in ExcitationTarget}
        function[self._pso_snapshot.excitation_target] = self._pso_snapshot.excitation_function

        context = ClosedLoopResponseContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
            kp=self._pos_result.kp,
            ti=self._pos_result.ti,
            td=self._pos_result.td,
            tf=self._pos_result.tf,
            t0=t0,
            t1=t1,
            solver=self._settings.get_solver(),
            anti_windup=self._pso_snapshot.controller_anti_windup,
            constraint=(
                self._pso_snapshot.controller_constraint_min,
                self._pso_snapshot.controller_constraint_max,
            ),
            reference=function.get(ExcitationTarget.REFERENCE).get_function(),
            input_disturbance=function.get(ExcitationTarget.INPUT_DISTURBANCE).get_function(),
            measurement_disturbance=function.get(ExcitationTarget.MEASUREMENT_DISTURBANCE).get_function(),
        )

        self._simulation_service.compute_closed_loop_response(context, self._on_closed_loop_compute_finished)

    def _on_closed_loop_compute_finished(self, t: ndarray, u: ndarray, y: ndarray) -> None:
        self.closedLoopResponseChanged.emit(t, u, y)

    @Slot(float, float)
    def compute_plant_response(self, t0: float, t1: float) -> None:
        if self._pos_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, plant response are not computed")
            return

        self.logger.debug("Running plant response.")

        function = NullFunction()
        if self._pso_snapshot.excitation_target == ExcitationTarget.REFERENCE:
            function = self._pso_snapshot.excitation_function

        context = PlantResponseContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
            t0=t0,
            t1=t1,
            solver=self._settings.get_solver(),
            reference=function.get_function()
        )

        self._simulation_service.compute_plant_response(context, self._on_plant_compute_finished)

    def _on_plant_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self.plantResponseChanged.emit(t, y)

    @Slot(float, float)
    def compute_function(self, t0: float, t1: float) -> None:
        if self._pos_result is None or self._pso_snapshot is None:
            self.logger.debug("No Result are available, function are not computed")
            return

        self.logger.debug("Running function.")

        # Avoid t0 being exactly zero for numerical reasons
        if t0 == 0:
            t0 = -sys.float_info.min
        t = linspace(t0, t1, 5000)

        function = self._pso_snapshot.excitation_function.get_function()
        self._simulation_service.compute_function(t, function, self._on_function_compute_finished)

    def _on_function_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self.functionChanged.emit(t, y)
