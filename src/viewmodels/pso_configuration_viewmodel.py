from PySide6.QtCore import QObject, Signal, Slot

from service import SimulationService
from app_domain.engine import PsoSimulationParam, PsoResult
from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from models import ModelContainer, PsoConfigurationModel, SettingsModel, PlantModel, FunctionModel, ControllerModel
from .base_viewmodel import BaseViewModel


class PsoConfigurationViewModel(BaseViewModel):

    xMinChanged = Signal()
    xMaxChanged = Signal()
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

        self._connect_signals()
        self.run_pso_simulation()

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    # -------------------
    # start time
    # -------------------
    def _verify_x_min(self, value: float) -> bool:
        if self._model_pso.x_max <= value:
            self.logger.debug(f"Skipped 'x_min' update (value={value} >= x_max={self._model_pso.x_max})")
            return False
        return True

    x_min: float = BaseViewModel._logged_property(
        attribute="_model_pso.x_min",
        notify_signal="xMinChanged",
        property_type=float,
        custom_setter=_verify_x_min
    )

    # -------------------
    # end time
    # -------------------
    def _verify_x_max(self, value: float) -> bool:
        if self._model_pso.x_min >= value:
            self.logger.debug(f"Skipped 'x_max' update (value={value} <= x_min={self._model_pso.x_min})")
            return False
        return True

    x_max: float = BaseViewModel._logged_property(
        attribute="_model_pso.x_max",
        notify_signal="xMaxChanged",
        property_type=float,
        custom_setter=_verify_x_max
    )

    # -------------------
    # excitation_target
    # -------------------
    excitation_target: ExcitationTarget = BaseViewModel._logged_property(
        attribute="_model_pso.excitation_target",
        notify_signal="excitationTargetChanged",
        property_type=ExcitationTarget
    )

    # -------------------
    # performance_index
    # -------------------
    performance_index: PerformanceIndex = BaseViewModel._logged_property(
        attribute="_model_pso.performance_index",
        notify_signal="performanceIndexChanged",
        property_type=PerformanceIndex
    )

    # -------------------
    # kp
    # -------------------
    def _verify_kp_min(self, value: float) -> bool:
        if self._model_pso.kp_max <= value:
            self.logger.debug(f"Skipped 'kp_min' update (value={value} >= kp_min={self._model_pso.kp_min})")
            return False
        return True

    kp_min: float = BaseViewModel._logged_property(
        attribute="_model_pso.kp_min",
        notify_signal="kpMinChanged",
        property_type=float,
        custom_setter=_verify_kp_min
    )

    def _verify_kp_max(self, value: float) -> bool:
        if self._model_pso.kp_min >= value:
            self.logger.debug(f"Skipped 'kp_max' update (value={value} <= kp_max={self._model_pso.kp_max})")
            return False
        return True

    kp_max: float = BaseViewModel._logged_property(
        attribute="_model_pso.kp_max",
        notify_signal="kpMaxChanged",
        property_type=float,
        custom_setter=_verify_kp_max
    )

    # -------------------
    # ti
    # -------------------
    def _verify_ti_min(self, value: float) -> float | None:
        if value == 0:
            value = 1e-9

        if self._model_pso.ti_max <= value:
            self.logger.debug(
                f"Skipped 'ti_min' update (value={value} >= ti_max={self._model_pso.ti_max})"
            )
            return None

        return value

    ti_min: float = BaseViewModel._logged_property(
        attribute="_model_pso.ti_min",
        notify_signal="tiMinChanged",
        property_type=float,
        custom_setter=_verify_ti_min
    )

    def _verify_ti_max(self, value: float) -> bool:
        if self._model_pso.ti_min >= value:
            self.logger.debug(f"Skipped 'ti_max' update (value={value} <= ti_max={self._model_pso.ti_max})")
            return False
        return True

    ti_max: float = BaseViewModel._logged_property(
        attribute="_model_pso.ti_max",
        notify_signal="tiMaxChanged",
        property_type=float,
        custom_setter=_verify_ti_max
    )

    # -------------------
    # td
    # -------------------
    def _verify_td_min(self, value: float) -> bool:
        if self._model_pso.td_max <= value:
            self.logger.debug(f"Skipped 'td_min' update (value={value} >= td_min={self._model_pso.td_min})")
            return False
        return True

    td_min: float = BaseViewModel._logged_property(
        attribute="_model_pso.td_min",
        notify_signal="tdMinChanged",
        property_type=float,
        custom_setter=_verify_td_min
    )

    def _verify_td_max(self, value: float) -> bool:
        if self._model_pso.td_min >= value:
            self.logger.debug(f"Skipped 'td_max' update (value={value} <= td_max={self._model_pso.td_max})")
            return False
        return True

    td_max: float = BaseViewModel._logged_property(
        attribute="_model_pso.td_max",
        notify_signal="tdMaxChanged",
        property_type=float,
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

        self._pos_iteration = self._settings.get_pso_iterations()

        self._simulation_service.run_pso_simulation(
            self._get_pos_param(), self._on_pso_simulation_finished, self._on_pso_progress
        )

    def _get_pos_param(self) -> PsoSimulationParam:
        return PsoSimulationParam(
            num=self._model_plant.num,
            den=self._model_plant.den,
            t0=self.x_min,
            t1=self.x_max,
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

    @Slot()
    def get_pso_result(self) -> PsoResult | None:
        return self._pso_result

    @Slot()
    def get_pos_iteration(self) -> int:
        return self._pos_iteration

    def _on_pso_progress(self, iteration: int) -> None:
        self.psoProgressChanged.emit(iteration)
