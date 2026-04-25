from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from app_domain.functions import resolve_function_type, FunctionTypes
from app_types import PsoSimulationParam
from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from utils import LoggedProperty
from models import PsoSimulationSnapshot
from .base_viewmodel import BaseViewModel
from app_types import PsoField

if TYPE_CHECKING:
    from service import SimulationService
    from app_types import PsoResult
    from models import ModelContainer, PsoConfigurationModel, SettingsModel, PlantModel, FunctionModel, ControllerModel
    from .controller_viewmodel import ControllerViewModel

class PsoConfigurationViewModel(BaseViewModel):
    t0Changed = Signal()
    t1Changed = Signal()
    excitationTargetChanged = Signal()
    performanceIndexChanged = Signal()
    overshootControlChanged = Signal()
    overshootControlEnabledChanged = Signal()
    overshootControlVisibilityChanged = Signal()
    slewRateMaxChanged = Signal()
    slewWindowSizeChanged = Signal()
    slewRateLimitEnabledChanged = Signal()
    gainMarginChanged = Signal()
    gainMarginEnabledChanged = Signal()
    phaseMarginChanged = Signal()
    phaseMarginEnabledChanged = Signal()
    stabilityMarginChanged = Signal()
    stabilityMarginEnabledChanged = Signal()
    lowerBoundsChanged = Signal(str)
    upperBoundsChanged = Signal(str)
    psoProgressChanged = Signal(int)
    psoSimulationFinished = Signal()
    psoSimulationInterrupted = Signal()

    def __init__(
            self,
            model_container: ModelContainer,
            vm_controller: ControllerViewModel,
            simulation_service: SimulationService,
            parent: QObject = None
    ) -> None:
        super().__init__(parent)

        self._model_plant: PlantModel = model_container.model_plant
        self._model_function: FunctionModel = model_container.ensure_function_model("excitation_target")
        self._model_controller: ControllerModel = model_container.model_controller
        self._model_pso: PsoConfigurationModel = model_container.model_pso
        self._settings: SettingsModel = model_container.model_settings

        self._vm_controller: ControllerViewModel = vm_controller
        self._simulation_service = simulation_service

        self._pos_iteration: int = 0
        self._pso_result: PsoResult | None = None
        self._pso_snapshot: PsoSimulationSnapshot | None = None

        self._overshoot_control_visibility: bool = self._get_overshoot_control_visibility()
        self._preserve_bounds_on_next_controller_sync = False

        self._connect_signals()
        self.run_pso_simulation()

    def _connect_signals(self) -> None:
        self._vm_controller.controllerTypeChanged.connect(self._on_vm_controller_changed)

    # ============================================================
    # start time
    # ============================================================
    def _verify_t0(self, value: float):

        result = self._validate_relation(
            valid=value < self._model_pso.t1,
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

    # ============================================================
    # end time
    # ============================================================
    def _verify_t1(self, value: float):

        result = self._validate_relation(
            valid=value > self._model_pso.t0,
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

    # ============================================================
    # excitation_target
    # ============================================================
    excitation_target: ExcitationTarget = LoggedProperty(
        path="_model_pso.excitation_target",
        signal="excitationTargetChanged",
        typ=ExcitationTarget
    )

    # ============================================================
    # error_criterion
    # ============================================================
    error_criterion: PerformanceIndex = LoggedProperty(
        path="_model_pso.error_criterion",
        signal="performanceIndexChanged",
        typ=PerformanceIndex
    )

    # ============================================================
    # overshoot control
    # ============================================================
    overshoot_control: float = LoggedProperty(
        path="_model_pso.overshoot_control",
        signal="overshootControlChanged",
        typ=float,
    )
    overshoot_control_enabled: bool = LoggedProperty(
        path="_model_pso.overshoot_control_enabled",
        signal="overshootControlEnabledChanged",
        typ=bool
    )
    overshoot_control_visibility: bool = LoggedProperty(
        path="_overshoot_control_visibility",
        signal="overshootControlVisibilityChanged",
        typ=bool,
    )

    @Slot()
    def check_overshoot_control_visibility(self) -> None:
        self.overshoot_control_visibility = self._get_overshoot_control_visibility()

    def _get_overshoot_control_visibility(self) -> bool:
        visible = self.excitation_target == ExcitationTarget.REFERENCE
        visible = visible and resolve_function_type(self._model_function.selected_function) == FunctionTypes.STEP
        return visible

    # ============================================================
    # slew rate limit
    # ============================================================
    slew_rate_max: float = LoggedProperty(
        path="_model_pso.slew_rate_max",
        signal="slewRateMaxChanged",
        typ=float,
    )

    slew_window_size: int = LoggedProperty(
        path="_model_pso.slew_window_size",
        signal="slewWindowSizeChanged",
        typ=int
    )

    slew_rate_limit_enabled: bool = LoggedProperty(
        path="_model_pso.slew_rate_limit_enabled",
        signal="slewRateLimitEnabledChanged",
        typ=bool
    )

    # ============================================================
    # gain margin
    # ============================================================
    gain_margin: float = LoggedProperty(
        path="_model_pso.gain_margin",
        signal="gainMarginChanged",
        typ=float,
    )
    gain_margin_enabled: bool = LoggedProperty(
        path="_model_pso.gain_margin_enabled",
        signal="gainMarginEnabledChanged",
        typ=bool
    )

    # ============================================================
    # phase margin
    # ============================================================
    phase_margin: float = LoggedProperty(
        path="_model_pso.phase_margin",
        signal="phaseMarginChanged",
        typ=float
    )
    phase_margin_enabled: bool = LoggedProperty(
        path="_model_pso.phase_margin_enabled",
        signal="phaseMarginEnabledChanged",
        typ=bool
    )

    # ============================================================
    # stability margin
    # ============================================================
    stability_margin: float = LoggedProperty(
        path="_model_pso.stability_margin",
        signal="stabilityMarginChanged",
        typ=float
    )
    stability_margin_enabled: bool = LoggedProperty(
        path="_model_pso.stability_margin_enabled",
        signal="stabilityMarginEnabledChanged",
        typ=bool
    )

    # ============================================================
    # Bounds
    # ============================================================
    @Slot()
    def get_lower_bounds(self) -> dict[str, float]:
        self.logger.debug(f"Getter 'lower_bounds' called (value={self._model_pso.lower_bounds})")
        return self._model_pso.lower_bounds

    @Slot(str, float)
    def set_lower_bound(self, key: str, value: float) -> None:
        self.logger.debug(f"Setter 'lower_bounds' called (key={key}: value={value})")

        field_key = f"{key}.{PsoField.PSO_LOWER_KEY.value}.{PsoField.PSO_BOUNDS_KEY.value}"

        result = self._validate_relation(
            valid=value >= self._model_pso.min_bounds[key],
            message=self.tr(
                "Invalid value: min ({value}) must be greater or equal than ({min})."
            ).format(value=value, min=self._model_pso.min_bounds[key])
        )

        if not self._verify(field_key, result):
            return

        result = self._validate_relation(
            valid=value <= self._model_pso.upper_bounds[key],
            message=self.tr(
                "Invalid value: min ({value}) must be smaller than max ({max})."
            ).format(value=value, max=self._model_pso.upper_bounds[key])
        )

        if not self._verify(field_key, result):
            return

        self._model_pso.lower_bounds[key] = value
        self.logger.debug(f"Emitting lowerBoundsChanged")
        self.lowerBoundsChanged.emit(key)

    @Slot()
    def get_upper_bounds(self) -> dict[str, float]:
        self.logger.debug(f"Getter 'upper_bounds' called (value={self._model_pso.upper_bounds})")
        return self._model_pso.upper_bounds

    @Slot(str, float)
    def set_upper_bound(self, key: str, value: float) -> None:
        self.logger.debug(f"Setter 'upper_bound' called (key={key}: value={value})")

        field_key = f"{key}.{PsoField.PSO_UPPER_KEY.value}.{PsoField.PSO_BOUNDS_KEY.value}"

        result = self._validate_relation(
            valid=value >= self._model_pso.lower_bounds[key],
            message=self.tr(
                "Invalid value: max ({value}) must be greater than min ({min})."
            ).format(value=value, min=self._model_pso.lower_bounds[key])
        )

        if not self._verify(field_key, result):
            return

        self._model_pso.upper_bounds[key] = value
        self.logger.debug(f"Emitting upperBoundsChanged")
        self.upperBoundsChanged.emit(key)

    # ============================================================
    # run PSO
    # ============================================================
    @Slot()
    def run_pso_simulation(self) -> None:
        self.logger.debug("Running PSO simulation")

        if not self._model_plant.is_valid:
            self.logger.debug("Model is invalid -> no (new) calculation")
            return

        self._pso_result = None
        self._pso_snapshot = self._create_model_snapshot()

        self._pos_iteration = self._settings.pso_repeat_runs

        self._simulation_service.run_pso_simulation(
            self._get_pos_param(), self._on_pso_simulation_finished, self._on_pso_progress
        )

    @Slot()
    def interrupt_pso_simulation(self) -> None:
        """Request interruption of the active PSO simulation."""
        self.logger.debug("Interrupting PSO simulation")
        self._simulation_service.stop_pso_simulation()
        self.psoSimulationInterrupted.emit()

    @Slot()
    def get_pso_result(self) -> PsoResult | None:
        return self._pso_result

    @Slot()
    def get_pso_snapshot(self) -> PsoSimulationSnapshot | None:
        return self._pso_snapshot

    @Slot()
    def get_pos_iteration(self) -> int:
        return self._pos_iteration

    @Slot()
    def preserve_bounds_on_next_controller_sync(self) -> None:
        self._preserve_bounds_on_next_controller_sync = True

    @Slot()
    def refresh_from_model(self) -> None:
        self._overshoot_control_visibility = self._get_overshoot_control_visibility()

        self.t0Changed.emit()
        self.t1Changed.emit()
        self.excitationTargetChanged.emit()
        self.performanceIndexChanged.emit()
        self.overshootControlChanged.emit()
        self.overshootControlEnabledChanged.emit()
        self.overshootControlVisibilityChanged.emit()
        self.slewRateMaxChanged.emit()
        self.slewWindowSizeChanged.emit()
        self.slewRateLimitEnabledChanged.emit()
        self.gainMarginChanged.emit()
        self.gainMarginEnabledChanged.emit()
        self.phaseMarginChanged.emit()
        self.phaseMarginEnabledChanged.emit()
        self.stabilityMarginChanged.emit()
        self.stabilityMarginEnabledChanged.emit()

        self._sync_controller_bounds(preserve_existing=True)

    # ============================================================
    # Internal helpers
    # ============================================================
    def _on_vm_controller_changed(self) -> None:
        """Reset bounds to controller defaults after an actual controller change."""
        preserve_existing = self._preserve_bounds_on_next_controller_sync
        self._preserve_bounds_on_next_controller_sync = False
        self._sync_controller_bounds(preserve_existing=preserve_existing)

    def _sync_controller_bounds(self, preserve_existing: bool) -> None:
        """Sync controller bounds, optionally preserving imported values during UI refresh."""
        spec = self._vm_controller.controller_spec
        lw, up = spec.bounds
        params = spec.param_names

        current_lower = self._model_pso.lower_bounds
        current_upper = self._model_pso.upper_bounds

        expected_keys = list(params)
        lower_keys_match = list(current_lower.keys()) == expected_keys
        upper_keys_match = list(current_upper.keys()) == expected_keys

        self._model_pso.min_bounds = {k: v for k, v in zip(params, spec.min_bounds)}

        if preserve_existing and lower_keys_match and upper_keys_match:
            self._model_pso.lower_bounds = {key: current_lower[key] for key in params}
            self._model_pso.upper_bounds = {key: current_upper[key] for key in params}
        else:
            self._model_pso.lower_bounds = {k: v for k, v in zip(params, lw)}
            self._model_pso.upper_bounds = {k: v for k, v in zip(params, up)}

        self._model_pso.n_params = len(lw)

        for key in params:
            self.lowerBoundsChanged.emit(key)
            self.upperBoundsChanged.emit(key)

    def _on_pso_progress(self, iteration: int) -> None:
        self.psoProgressChanged.emit(iteration)

    def _get_pos_param(self) -> PsoSimulationParam:
        return PsoSimulationParam(
            num=self._model_plant.num,
            den=self._model_plant.den,
            controller_type=self._model_controller.controller_type,
            controller_param_names=self._model_controller.controller_spec.param_names,
            controller_class=self._model_controller.controller_spec.controller_class,
            t0=self.t0,
            t1=self.t1,
            dt=self._settings.time_step,
            tuning_factor=self._model_controller.tuning_factor,
            limit_factor=5.0,
            sampling_rate=self._model_controller.sampling_rate,
            solver=self._settings.solver,
            anti_windup=self._model_controller.anti_windup,
            ka=self._model_controller.ka,
            constraint=(
                self._model_controller.constraint_min,
                self._model_controller.constraint_max,
            ),
            excitation_target=self.excitation_target,
            function=self._model_function.selected_function.copy(),
            bounds=(
                [b for b in self._model_pso.lower_bounds.values()],
                [b for b in self._model_pso.upper_bounds.values()],
            ),
            n_param=self._model_pso.n_params,
            swarm_size=self._settings.pso_swarm_size,
            pso_iteration=self._pos_iteration,
            error_criterion=self.error_criterion,
            slew_rate_max=self._model_pso.slew_rate_max,
            slew_window_size=self._model_pso.slew_window_size,
            slew_rate_limit_enabled=self._model_pso.slew_rate_limit_enabled,
            overshoot_control=self._model_pso.overshoot_control,
            overshoot_control_enabled=self._model_pso.overshoot_control_enabled and self._overshoot_control_visibility,
            gain_margin=self._model_pso.gain_margin,
            gain_margin_enabled=self._model_pso.gain_margin_enabled,
            phase_margin=self._model_pso.phase_margin,
            phase_margin_enabled=self._model_pso.phase_margin_enabled,
            stability_margin=self._model_pso.stability_margin,
            stability_margin_enabled=self._model_pso.stability_margin_enabled,
            omega_exp_low=-5,
            omega_exp_high=5,
            omega_points=500,
            hyperparameters=self._settings.get_pso_hyper_parameters(),
        )

    def _on_pso_simulation_finished(self, result: PsoResult):
        self._pso_result = result
        self.psoSimulationFinished.emit()

    def _create_model_snapshot(self) -> PsoSimulationSnapshot:
        return PsoSimulationSnapshot(
            plant_num=tuple(self._model_plant.num),
            plant_den=tuple(self._model_plant.den),
            plant_tf=self._model_plant.tf,
            controller_type=self._model_controller.controller_type,
            controller_anti_windup=self._model_controller.anti_windup,
            controller_ka=self._model_controller.ka,
            controller_constraint_min=self._model_controller.constraint_min,
            controller_constraint_max=self._model_controller.constraint_max,
            controller_tuning_factor=self._model_controller.tuning_factor,
            sampling_rate=self._model_controller.sampling_rate,
            simulation_time=(self._model_pso.t0, self._model_pso.t1),
            excitation_target=self._model_pso.excitation_target,
            excitation_function=self._model_function.selected_function.copy(),
            error_criterion=self._model_pso.error_criterion,
            bounds=(
                [b for b in self._model_pso.lower_bounds.values()],
                [b for b in self._model_pso.upper_bounds.values()],
            ),
            n_param=self._model_pso.n_params,
            overshoot_control=self._model_pso.overshoot_control,
            overshoot_control_enabled=self._model_pso.overshoot_control_enabled,
            slew_rate_max=self._model_pso.slew_rate_max,
            slew_window_size=self._model_pso.slew_window_size,
            slew_rate_limit_enabled=self._model_pso.slew_rate_limit_enabled,
            gain_margin=self._model_pso.gain_margin,
            gain_margin_enabled=self._model_pso.gain_margin_enabled,
            phase_margin=self._model_pso.phase_margin,
            phase_margin_enabled=self._model_pso.phase_margin_enabled,
            stability_margin=self._model_pso.stability_margin,
            stability_margin_enabled=self._model_pso.stability_margin_enabled,
        )
