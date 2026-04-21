from __future__ import annotations
from typing import TYPE_CHECKING
from numpy import ndarray

from PySide6.QtCore import QObject, Signal, Slot

from app_domain.functions import NullFunction
from app_types import ClosedLoopResponseContext, PlantResponseContext
from app_domain.controlsys import ExcitationTarget
from utils import LoggedProperty
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from service import SimulationService
    from app_types import PsoResult
    from models import SettingsModel, FunctionModel, PsoSimulationSnapshot
    from viewmodels.pso_configuration_viewmodel import PsoConfigurationViewModel

class SimulationViewModel(BaseViewModel):
    psoSimulationFinished = Signal()
    closedLoopResponseChanged = Signal(ndarray, ndarray, ndarray)
    plantResponseChanged = Signal(ndarray, ndarray)

    def __init__(
            self,
            model_functions: dict[str, FunctionModel],
            settings: SettingsModel,
            vm_pso: PsoConfigurationViewModel,
            simulation_service: SimulationService,
            parent: QObject = None
    ) -> None:
        super().__init__(parent)

        self._model_functions = model_functions
        self._settings: SettingsModel = settings
        self._pos_result: PsoResult | None = None
        self._pso_snapshot: PsoSimulationSnapshot | None = None

        self._vm_pso = vm_pso
        self._simulation_service = simulation_service

        self._connect_signals()
        self._on_pso_simulation_finished()

    def _connect_signals(self) -> None:
        # Pull fresh evaluation values whenever a new PSO run completes.
        self._vm_pso.psoSimulationFinished.connect(self._on_pso_simulation_finished)

    t0 = LoggedProperty(
        path="_pos_result.t0",
        typ=float,
        read_only=True
    )

    t1 = LoggedProperty(
        path="_pos_result.t1",
        typ=float,
        read_only=True
    )

    excitation_target = LoggedProperty(
        path="_pso_snapshot.excitation_target",
        typ=ExcitationTarget,
        read_only=True
    )

    def _on_pso_simulation_finished(self) -> None:
        self._pos_result = self._vm_pso.get_pso_result()
        self._pso_snapshot = self._vm_pso.get_pso_snapshot()

        if self._pso_snapshot is None:
            self.logger.warning("PSO snapshot is None; skipping psoSimulationFinished emit.")
            return

        # reset the functions to NullFunction
        for model in self._model_functions.values():
            model.selected_function = NullFunction()

        function_model = self._model_functions.get(self._pso_snapshot.excitation_target.name)
        if function_model is not None:
            function_model.selected_function = self._pso_snapshot.excitation_function.copy()

        self.psoSimulationFinished.emit()

    def has_result(self) -> bool:
        return self._pos_result is not None

    def has_snapshot(self) -> bool:
        return self._pso_snapshot is not None

    @Slot(float, float)
    def compute_closed_loop_response(self, t0: float, t1: float) -> None:
        if self._pos_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, closed loop response are not computed")
            return

        self.logger.debug("Running closed loop response.")

        context = ClosedLoopResponseContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
            kp=self._pos_result.kp,
            ti=self._pos_result.ti,
            td=self._pos_result.td,
            tf=self._pos_result.tf,
            t0=t0,
            t1=t1,
            solver=self._settings.solver,
            anti_windup=self._pso_snapshot.controller_anti_windup,
            ka=self._pso_snapshot.controller_ka,
            constraint=(
                self._pso_snapshot.controller_constraint_min,
                self._pso_snapshot.controller_constraint_max,
            ),
            reference=self._model_functions.get(
                ExcitationTarget.REFERENCE.name).selected_function.get_function(),
            input_disturbance=self._model_functions.get(
                ExcitationTarget.INPUT_DISTURBANCE.name).selected_function.get_function(),
            measurement_disturbance=self._model_functions.get(
                ExcitationTarget.MEASUREMENT_DISTURBANCE.name).selected_function.get_function()
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

        context = PlantResponseContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
            t0=t0,
            t1=t1,
            solver=self._settings.solver,
            reference=self._model_functions.get(
                ExcitationTarget.REFERENCE.name).selected_function.get_function()
        )

        self._simulation_service.compute_plant_response(context, self._on_plant_compute_finished)

    def _on_plant_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self.plantResponseChanged.emit(t, y)
