from PySide6.QtCore import QObject, Signal, Slot

from service import SimulationService
from app_domain.engine.types import PsoSimulationParam, PsoResult
from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from models import (
    ModelContainer,
    PsoConfigurationModel,
    SettingsModel,
    PlantModel,
    FunctionModel,
    ControllerModel,
    PsoSimulationSnapshot,
)
from utils import LoggedProperty
from .base_viewmodel import BaseViewModel
from .types import PsoField


class PsoConfigurationViewModel(BaseViewModel):
    t0Changed = Signal()
    t1Changed = Signal()
    excitationTargetChanged = Signal()
    performanceIndexChanged = Signal()
    kpMinChanged = Signal()
    kpMaxChanged = Signal()
    tiMinChanged = Signal()
    tiMaxChanged = Signal()
    tdMinChanged = Signal()
    tdMaxChanged = Signal()
    psoProgressChanged = Signal(int)
    psoSimulationFinished = Signal()

    def __init__(self, model_container: ModelContainer, simulation_service: SimulationService,
                 parent: QObject = None) -> None:
        super().__init__(parent)

        self._model_plant: PlantModel = model_container.model_plant
        self._model_function: FunctionModel = model_container.ensure_function_model("excitation_target")
        self._model_controller: ControllerModel = model_container.model_controller
        self._model_pso: PsoConfigurationModel = model_container.model_pso
        self._settings: SettingsModel = model_container.model_settings
        self._simulation_service = simulation_service

        self._pos_iteration: int = 0
        self._pso_result: PsoResult | None = None
        self._pso_snapshot: PsoSimulationSnapshot | None = None

        self._connect_signals()
        self.run_pso_simulation()

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    # -------------------
    # start time
    # -------------------
    def _verify_t0(self, value: float):

        result = self._validate_relation(
            value=value,
            other=self._model_pso.t1,
            relation="<",
            message=self.tr(
                "Invalid value: start time ({t0}) must be smaller than end time ({t1})."
            ).format(t0=value, t1=self._model_pso.t1)
        )

        return self._verify(PsoField.T0, result)

    t0: float = LoggedProperty(
        path="_model_pso.t0",
        signal="t0Changed",
        typ=float,
        custom_setter=_verify_t0
    )

    # -------------------
    # end time
    # -------------------
    def _verify_t1(self, value: float):

        result = self._validate_relation(
            value=value,
            other=self._model_pso.t0,
            relation=">",
            message=self.tr(
                "Invalid value: end time ({t1}) must be greater than start time ({t0})."
            ).format(t1=value, t0=self._model_pso.t0)
        )

        return self._verify(PsoField.T1, result)

    t1: float = LoggedProperty(
        path="_model_pso.t1",
        signal="t1Changed",
        typ=float,
        custom_setter=_verify_t1
    )

    # -------------------
    # excitation_target
    # -------------------
    excitation_target: ExcitationTarget = LoggedProperty(
        path="_model_pso.excitation_target",
        signal="excitationTargetChanged",
        typ=ExcitationTarget
    )

    # -------------------
    # performance_index
    # -------------------
    performance_index: PerformanceIndex = LoggedProperty(
        path="_model_pso.performance_index",
        signal="performanceIndexChanged",
        typ=PerformanceIndex
    )

    # -------------------
    # kp
    # -------------------
    def _verify_kp_min(self, value: float):

        result = self._validate_relation(
            value=value,
            other=self._model_pso.kp_max,
            relation="<",
            message=self.tr(
                "Invalid value: min ({value}) must be smaller than max ({max})."
            ).format(value=value, max=self._model_pso.kp_max)
        )

        return self._verify(PsoField.KP_MIN, result)

    kp_min: float = LoggedProperty(
        path="_model_pso.kp_min",
        signal="kpMinChanged",
        typ=float,
        custom_setter=_verify_kp_min
    )

    def _verify_kp_max(self, value: float):

        result = self._validate_relation(
            value=value,
            other=self._model_pso.kp_min,
            relation=">",
            message=self.tr(
                "Invalid value: max ({value}) must be greater than min ({min})."
            ).format(value=value, min=self._model_pso.kp_min)
        )

        return self._verify(PsoField.KP_MAX, result)

    kp_max: float = LoggedProperty(
        path="_model_pso.kp_max",
        signal="kpMaxChanged",
        typ=float,
        custom_setter=_verify_kp_max
    )

    # -------------------
    # ti
    # -------------------
    def _verify_ti_min(self, value: float):

        if value == 0:
            value = 1e-9

        result = self._validate_relation(
            value=value,
            other=self._model_pso.ti_max,
            relation="<",
            message=self.tr(
                "Invalid value: min ({value}) must be smaller than max ({max})."
            ).format(value=value, max=self._model_pso.ti_max)
        )

        if not self._verify(PsoField.TI_MIN, result):
            return False

        return value

    ti_min: float = LoggedProperty(
        path="_model_pso.ti_min",
        signal="tiMinChanged",
        typ=float,
        custom_setter=_verify_ti_min
    )

    def _verify_ti_max(self, value: float) -> bool:

        result = self._validate_relation(
            value=value,
            other=self._model_pso.ti_min,
            relation=">",
            message=self.tr(
                "Invalid value: max ({value}) must be greater than min ({min})."
            ).format(value=value, min=self._model_pso.ti_min)
        )

        return self._verify(PsoField.TI_MAX, result)

    ti_max: float = LoggedProperty(
        path="_model_pso.ti_max",
        signal="tiMaxChanged",
        typ=float,
        custom_setter=_verify_ti_max
    )

    # -------------------
    # td
    # -------------------
    def _verify_td_min(self, value: float) -> bool:

        result = self._validate_relation(
            value=value,
            other=self._model_pso.td_max,
            relation="<",
            message=self.tr(
                "Invalid value: min ({value}) must be smaller than max ({max})."
            ).format(value=value, max=self._model_pso.td_max)
        )

        return self._verify(PsoField.TD_MIN, result)

    td_min: float = LoggedProperty(
        path="_model_pso.td_min",
        signal="tdMinChanged",
        typ=float,
        custom_setter=_verify_td_min
    )

    def _verify_td_max(self, value: float) -> bool:

        result = self._validate_relation(
            value=value,
            other=self._model_pso.td_min,
            relation=">",
            message=self.tr(
                "Invalid value: max ({value}) must be greater than min ({min})."
            ).format(value=value, min=self._model_pso.td_min)
        )

        return self._verify(PsoField.TD_MAX, result)

    td_max: float = LoggedProperty(
        path="_model_pso.td_max",
        signal="tdMaxChanged",
        typ=float,
        custom_setter=_verify_td_max
    )

    # -------------------
    # run PSO
    # -------------------
    @Slot()
    def run_pso_simulation(self) -> None:
        self.logger.debug("Running PSO simulation")

        if not self._model_plant.is_valid:
            self.logger.debug("Model is invalid -> no (new) calculation")
            return

        self._pso_result = None
        self._pso_snapshot = self._create_model_snapshot()

        self._pos_iteration = self._settings.get_pso_iterations()

        self._simulation_service.run_pso_simulation(
            self._get_pos_param(), self._on_pso_simulation_finished, self._on_pso_progress
        )

    def _get_pos_param(self) -> PsoSimulationParam:
        return PsoSimulationParam(
            num=self._model_plant.num,
            den=self._model_plant.den,
            t0=self.t0,
            t1=self.t1,
            dt=self._settings.get_time_step(),
            solver=self._settings.get_solver(),
            anti_windup=self._model_controller.anti_windup,
            constraint=(
                self._model_controller.constraint_min,
                self._model_controller.constraint_max,
            ),
            excitation_target=self.excitation_target,
            function=self._model_function.selected_function.copy(),
            performance_index=self.performance_index,
            kp=(self.kp_min, self.kp_max),
            ti=(self.ti_min, self.ti_max),
            td=(self.td_min, self.td_max),
            swarm_size=self._settings.get_pso_particle(),
            pso_iteration=self._pos_iteration
        )

    def _on_pso_simulation_finished(self, result: PsoResult):
        self._pso_result = result
        self.psoSimulationFinished.emit()

    def _create_model_snapshot(self) -> PsoSimulationSnapshot:
        return PsoSimulationSnapshot(
            plant_num=tuple(self._model_plant.num),
            plant_den=tuple(self._model_plant.den),
            plant_tf=self._model_plant.tf,
            controller_anti_windup=self._model_controller.anti_windup,
            controller_constraint_min=self._model_controller.constraint_min,
            controller_constraint_max=self._model_controller.constraint_max,
            excitation_target=self.excitation_target,
            excitation_function=self._model_function.selected_function.copy(),
        )

    @Slot()
    def get_pso_result(self) -> PsoResult | None:
        return self._pso_result

    @Slot()
    def get_pso_snapshot(self) -> PsoSimulationSnapshot | None:
        return self._pso_snapshot

    @Slot()
    def get_pos_iteration(self) -> int:
        return self._pos_iteration

    def _on_pso_progress(self, iteration: int) -> None:
        self.psoProgressChanged.emit(iteration)
