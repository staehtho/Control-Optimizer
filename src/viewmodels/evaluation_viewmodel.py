from __future__ import annotations
from typing import TYPE_CHECKING
import sys
from numpy import ndarray, linspace

from PySide6.QtCore import QObject, Signal, Slot

from app_types import (
    PlantResponseContext, ClosedLoopResponseContext, PlantTransferContext, ControllerTransferContext, TransferFunctions
)
from app_domain.controlsys import ExcitationTarget, AntiWindup
from app_domain.functions import NullFunction
from utils import LoggedProperty
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from service import SimulationService
    from app_types import PsoResult
    from app_domain.functions import BaseFunction
    from models import SettingsModel, PsoSimulationSnapshot
    from viewmodels import PsoConfigurationViewModel

class EvaluationViewModel(BaseViewModel):
    """Exposes controller evaluation values and keeps them synced with PSO output."""
    psoSimulationFinished = Signal()
    closedLoopResponseChanged = Signal(ndarray, ndarray, ndarray)
    plantResponseChanged = Signal(ndarray, ndarray)
    functionChanged = Signal(ndarray, ndarray)
    plantFrequencyResponseChanged = Signal(object)
    closedLoopFrequencyResponseChanged = Signal(object)
    timeDomainPendingChanged = Signal(bool)
    frequencyDomainPendingChanged = Signal(bool)

    def __init__(
            self,
            settings: SettingsModel,
            vm_pso: PsoConfigurationViewModel,
            simulation_service: SimulationService,
            parent: QObject = None
    ) -> None:
        super().__init__(parent)

        self._settings = settings
        self._pso_result: PsoResult | None = None
        self._pso_snapshot: PsoSimulationSnapshot | None = None

        self._vm_pso = vm_pso
        self._simulation_service = simulation_service
        self._closed_loop_request_id: int = 0
        self._plant_response_request_id: int = 0
        self._function_request_id: int = 0
        self._plant_frequency_request_id: int = 0
        self._closed_loop_frequency_request_id: int = 0
        self._time_domain_pending_count: int = 0
        self._frequency_domain_pending_count: int = 0

        self._connect_signals()
        self._on_pso_simulation_finished()

    def _connect_signals(self) -> None:
        # Pull fresh evaluation values whenever a new PSO run completes.
        self._vm_pso.psoSimulationFinished.connect(self._on_pso_simulation_finished)

    t0 = LoggedProperty(
        path="_pso_result.t0",
        typ=float,
        read_only=True
    )

    t1 = LoggedProperty(
        path="_pso_result.t1",
        typ=float,
        read_only=True
    )

    excitation_target = LoggedProperty(
        path="_pso_snapshot.excitation_target",
        typ=ExcitationTarget,
        read_only=True
    )

    anti_windup = LoggedProperty(
        path="_pso_snapshot.controller_anti_windup",
        typ=AntiWindup,
        read_only=True
    )

    constraint_min = LoggedProperty(
        path="_pso_snapshot.controller_constraint_min",
        typ=float,
        read_only=True
    )

    constraint_max = LoggedProperty(
        path="_pso_snapshot.controller_constraint_max",
        typ=float,
        read_only=True
    )

    def _on_pso_simulation_finished(self) -> None:
        self._pso_result = self._vm_pso.get_pso_result()
        self._pso_snapshot = self._vm_pso.get_pso_snapshot()

        self.psoSimulationFinished.emit()

    @Slot()
    def get_pso_result(self) -> PsoResult | None:
        return self._pso_result

    @Slot()
    def get_pso_snapshot(self) -> PsoSimulationSnapshot | None:
        return self._pso_snapshot

    def has_result(self) -> bool:
        return self._pso_result is not None

    def has_snapshot(self) -> bool:
        return self._pso_snapshot is not None

    @Slot()
    def get_transfer_functions(self) -> TransferFunctions:
        return TransferFunctions(
            plant=r"G(s) = " + self._pso_snapshot.plant_tf if self._pso_snapshot is not None else "",
            controller=self._pso_snapshot.controller_spec.tf_controller if self._pso_snapshot is not None else "",
            open_loop=self._pso_snapshot.controller_spec.tf_open_loop if self._pso_snapshot is not None else "",
            closed_loop=self._pso_snapshot.controller_spec.tf_close_loop if self._pso_snapshot is not None else "",
            sensitivity=self._pso_snapshot.controller_spec.tf_sensitivity if self._pso_snapshot is not None else "",
        )


    @Slot(float, float)
    def compute_closed_loop_response(self, t0: float, t1: float) -> None:
        if self._pso_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, closed loop response are not computed")
            self._reset_time_domain_pending()
            return

        self._closed_loop_request_id += 1
        request_id = self._closed_loop_request_id
        self.logger.debug("Running closed loop response.")

        function: dict[ExcitationTarget, BaseFunction] = {target: NullFunction() for target in ExcitationTarget}
        function[self._pso_snapshot.excitation_target] = self._pso_snapshot.excitation_function

        context = ClosedLoopResponseContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
            controller=self._pso_snapshot.controller_spec.controller_class,
            controller_params=self._pso_result.best_params,
            t0=t0,
            t1=t1,
            dt=self._settings.time_step,
            solver=self._settings.solver,
            anti_windup=self._pso_snapshot.controller_anti_windup,
            ka=self._pso_snapshot.controller_ka,
            constraint=(
                self._pso_snapshot.controller_constraint_min,
                self._pso_snapshot.controller_constraint_max,
            ),
            reference=function[ExcitationTarget.REFERENCE].get_function(),
            input_disturbance=function[ExcitationTarget.INPUT_DISTURBANCE].get_function(),
            measurement_disturbance=function[ExcitationTarget.MEASUREMENT_DISTURBANCE].get_function(),
        )

        self._begin_time_domain_pending()
        self._simulation_service.compute_closed_loop_response(
            context,
            lambda t, u, y, req_id=request_id: self._on_closed_loop_compute_finished(req_id, t, u, y),
        )

    def _on_closed_loop_compute_finished(self, request_id: int, t: ndarray, u: ndarray, y: ndarray) -> None:
        self._end_time_domain_pending()
        if request_id != self._closed_loop_request_id:
            self.logger.debug("Ignoring stale closed-loop evaluation result (request_id=%s)", request_id)
            return

        self.closedLoopResponseChanged.emit(t, u, y)

    @Slot(float, float)
    def compute_plant_response(self, t0: float, t1: float) -> None:
        if self._pso_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, plant response are not computed")
            self._reset_time_domain_pending()
            return

        self._plant_response_request_id += 1
        request_id = self._plant_response_request_id
        self.logger.debug("Running plant response.")

        function = NullFunction()
        if self._pso_snapshot.excitation_target == ExcitationTarget.REFERENCE:
            function = self._pso_snapshot.excitation_function

        context = PlantResponseContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
            t0=t0,
            t1=t1,
            dt=self._settings.time_step,
            solver=self._settings.solver,
            reference=function.get_function()
        )

        self._begin_time_domain_pending()
        self._simulation_service.compute_plant_response(
            context,
            lambda t, y, req_id=request_id: self._on_plant_compute_finished(req_id, t, y),
        )

    def _on_plant_compute_finished(self, request_id: int, t: ndarray, y: ndarray) -> None:
        self._end_time_domain_pending()
        if request_id != self._plant_response_request_id:
            self.logger.debug("Ignoring stale plant evaluation result (request_id=%s)", request_id)
            return

        self.plantResponseChanged.emit(t, y)

    @Slot(float, float)
    def compute_function(self, t0: float, t1: float) -> None:
        if self._pso_result is None or self._pso_snapshot is None:
            self.logger.debug("No Result are available, function are not computed")
            self._reset_time_domain_pending()
            return

        self._function_request_id += 1
        request_id = self._function_request_id
        self.logger.debug("Running function.")

        # Avoid t0 being exactly zero for numerical reasons
        if t0 == 0:
            t0 = -sys.float_info.min
        t = linspace(t0, t1, 5000)

        function = self._pso_snapshot.excitation_function.get_function()
        self._begin_time_domain_pending()
        self._simulation_service.compute_function(
            t,
            function,
            lambda time, values, req_id=request_id: self._on_function_compute_finished(req_id, time, values),
        )

    def _on_function_compute_finished(self, request_id: int, t: ndarray, y: ndarray) -> None:
        self._end_time_domain_pending()
        if request_id != self._function_request_id:
            self.logger.debug("Ignoring stale evaluation function result (request_id=%s)", request_id)
            return

        self.functionChanged.emit(t, y)

    @Slot(float, float)
    def compute_plant_frequency_response(self, omega_min: float, omega_max: float) -> None:
        if self._pso_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, plant frequency response are not computed")
            self._reset_frequency_domain_pending()
            return

        self._plant_frequency_request_id += 1
        request_id = self._plant_frequency_request_id
        self.logger.debug("Running plant frequency response.")

        context = PlantTransferContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
        )

        self._begin_frequency_domain_pending()
        self._simulation_service.compute_plant_transfer_response(
            context,
            omega_min=omega_min,
            omega_max=omega_max,
            callback=lambda result, req_id=request_id: self._on_plant_frequency_response_finished(req_id, result),
        )

    def _on_plant_frequency_response_finished(self, request_id: int, result) -> None:
        self._end_frequency_domain_pending()
        if request_id != self._plant_frequency_request_id:
            self.logger.debug("Ignoring stale plant frequency result (request_id=%s)", request_id)
            return

        self.plantFrequencyResponseChanged.emit(result)

    @Slot(float, float)
    def compute_closed_loop_frequency_response(self, omega_min: float, omega_max: float) -> None:
        if self._pso_result is None or self._pso_snapshot is None:
            self.logger.debug("Plant is not valid, closed loop frequency response are not computed")
            self._reset_frequency_domain_pending()
            return

        self._closed_loop_frequency_request_id += 1
        request_id = self._closed_loop_frequency_request_id
        self.logger.debug("Running closed loop frequency response.")

        context_plant = PlantTransferContext(
            num=list(self._pso_snapshot.plant_num),
            den=list(self._pso_snapshot.plant_den),
        )

        context_controller = ControllerTransferContext(
            self._pso_snapshot.controller_spec.controller_class,
            self._pso_result.best_params
        )

        self._begin_frequency_domain_pending()
        self._simulation_service.compute_closed_loop_transfer_response(
            context_plant=context_plant,
            context_control=context_controller,
            omega_min=omega_min,
            omega_max=omega_max,
            callback=lambda result, req_id=request_id: self._on_closed_loop_frequency_response_finished(req_id, result)
        )

    def _on_closed_loop_frequency_response_finished(self, request_id: int, result) -> None:
        self._end_frequency_domain_pending()
        if request_id != self._closed_loop_frequency_request_id:
            self.logger.debug("Ignoring stale closed-loop frequency result (request_id=%s)", request_id)
            return

        self.closedLoopFrequencyResponseChanged.emit(result)

    def _begin_time_domain_pending(self) -> None:
        self._time_domain_pending_count += 1
        if self._time_domain_pending_count == 1:
            self.timeDomainPendingChanged.emit(True)

    def _end_time_domain_pending(self) -> None:
        if self._time_domain_pending_count == 0:
            return

        self._time_domain_pending_count -= 1
        if self._time_domain_pending_count == 0:
            self.timeDomainPendingChanged.emit(False)

    def _reset_time_domain_pending(self) -> None:
        if self._time_domain_pending_count == 0:
            return

        self._time_domain_pending_count = 0
        self.timeDomainPendingChanged.emit(False)

    def _begin_frequency_domain_pending(self) -> None:
        self._frequency_domain_pending_count += 1
        if self._frequency_domain_pending_count == 1:
            self.frequencyDomainPendingChanged.emit(True)

    def _end_frequency_domain_pending(self) -> None:
        if self._frequency_domain_pending_count == 0:
            return

        self._frequency_domain_pending_count -= 1
        if self._frequency_domain_pending_count == 0:
            self.frequencyDomainPendingChanged.emit(False)

    def _reset_frequency_domain_pending(self) -> None:
        if self._frequency_domain_pending_count == 0:
            return

        self._frequency_domain_pending_count = 0
        self.frequencyDomainPendingChanged.emit(False)
