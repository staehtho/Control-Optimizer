from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from app_types import (
    DynamicReportData, DynamicReportPlant, DynamicReportExcitationFunction,
    DynamicReportControllerConfiguration, DynamicReportPsoConfiguration, DynamicReportPsoResult,
    DynamicReportBlockDiagram, DynamicReportTimeDomainPlot, DynamicReportBodePlot, DynamicReportTransferFunctions
)
from resources.resources import OUTPUT_DIR, OutputFiles
from service.reporting import DynamicReport
from utils import LoggedProperty
from . import EvaluationViewModel
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from models import ModelContainer, ReportModel, PsoConfigurationModel


class ReportViewModel(BaseViewModel):
    includePlantChanged = Signal()
    includeExcitationFunctionChanged = Signal()
    includeControllerConfigurationChanged = Signal()
    includePsoConfigurationChanged = Signal()
    includePsoResultChanged = Signal()
    includeBlockDiagramChanged = Signal()
    includeTimeDomainPlotChanged = Signal()
    includeBodePlotChanged = Signal()
    includeTransferFunctionsChanged = Signal()
    reportFinished = Signal()

    def __init__(self, vm_evaluator: EvaluationViewModel, model_container: ModelContainer, parent: QObject = None):
        super().__init__(parent)

        self._vm_evaluator = vm_evaluator
        self._model_report: ReportModel = model_container.model_report
        self._model_pso: PsoConfigurationModel = model_container.model_pso

    # ============================================================
    # Property
    # ============================================================
    include_plant: bool = LoggedProperty(
        path="_model_report.plant",
        signal="includePlantChanged",
        typ=bool,
    )

    include_excitation_function: bool = LoggedProperty(
        path="_model_report.excitation_function",
        signal="includeExcitationFunctionChanged",
        typ=bool,
    )

    include_controller_configuration: bool = LoggedProperty(
        path="_model_report.controller_configuration",
        signal="includeControllerConfigurationChanged",
        typ=bool,
    )

    include_pso_configuration: bool = LoggedProperty(
        path="_model_report.pso_configuration",
        signal="includePsoConfigurationChanged",
        typ=bool,
    )

    include_pso_result: bool = LoggedProperty(
        path="_model_report.pso_result",
        signal="includePsoResultChanged",
        typ=bool,
    )

    include_block_diagram: bool = LoggedProperty(
        path="_model_report.block_diagram",
        signal="includeBlockDiagramChanged",
        typ=bool,
    )

    include_time_domain_plot: bool = LoggedProperty(
        path="_model_report.time_domain_plot",
        signal="includeTimeDomainPlotChanged",
        typ=bool,
    )

    include_bode_plot: bool = LoggedProperty(
        path="_model_report.bode_plot",
        signal="includeBodePlotChanged",
        typ=bool,
    )

    include_transfer_functions: bool = LoggedProperty(
        path="_model_report.transfer_functions",
        signal="includeTransferFunctionsChanged",
        typ=bool,
    )

    # ============================================================
    # Report
    # ============================================================
    @Slot()
    def generate_report(self) -> None:
        plant_data = self._get_plant_data()
        if plant_data is None:
            return

        excitation_function_data = self._get_excitation_function_data()
        if excitation_function_data is None:
            return

        controller_configuration_data = self._get_controller_configuration_data()
        if controller_configuration_data is None:
            return

        '''report_data = DynamicReportData(
            plant_data=plant_data,
            excitation_function_data=excitation_function_data,
            controller_configuration_data=controller_configuration_data,
            pso_configuration_data=self._get_pso_configuration_data(),
            pso_result_data=pso_result_data,
            block_diagram_data=block_diagram_data,
            time_domain_plot_data=time_domain_data,
            bode_plot_data=bode_plot_data,
            transfer_functions_data=transfer_function_data,
        )'''

        self.reportFinished.emit()

    # ============================================================
    # Internal Helper
    # ============================================================
    def _get_plant_data(self) -> DynamicReportPlant | None:
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return None
        return DynamicReportPlant(
            formula=snapshot.plant_tf,
        )

    def _get_excitation_function_data(self) -> DynamicReportExcitationFunction | None:
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return None
        return DynamicReportExcitationFunction(
            formula=snapshot.excitation_function.get_formula(),
            parameters=snapshot.excitation_function.get_param()
        )

    def _get_controller_configuration_data(self) -> DynamicReportControllerConfiguration | None:
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return None
        return DynamicReportControllerConfiguration(
            controller_type=snapshot.controller_type,
            anti_windup=snapshot.controller_anti_windup,
            factor_ka=snapshot.controller_ka,
            constraint_min=snapshot.controller_constraint_min,
            constraint_max=snapshot.controller_constraint_max,
            factor_n=snapshot.controller_tuning_factor,
            min_sampling_rate=snapshot.sampling_rate,
        )

    def _get_pso_configuration_data(self) -> DynamicReportPsoConfiguration:
        # TODO: add all pso configuration in the snapshot
        return DynamicReportPsoConfiguration(
            simulation_time=(self._model_pso.t0, self._model_pso.t1),
            excitation_target=self._model_pso.excitation_target,
            error_criterion=self._model_pso.error_criterion,
            overshoot_control=self._model_pso.overshoot_control if self._model_pso.overshoot_control_enabled else None,
            slew_rate_max=self._model_pso.slew_rate_max if self._model_pso.slew_rate_limit_enabled else None,
            slew_rate_window_size=self._model_pso.slew_window_size if self._model_pso.slew_rate_limit_enabled else None,
            gain_margin=self._model_pso.gain_margin if self._model_pso.gain_margin_enabled else None,
            phase_margin=self._model_pso.phase_margin if self._model_pso.phase_margin_enabled else None,
            stability=self._model_pso.stability_margin if self._model_pso.stability_margin_enabled else None,
            pso_bounds_parameters={
                "kp": (self._model_pso.kp_min, self._model_pso.kp_max),
                "ti": (self._model_pso.ti_min, self._model_pso.ti_max),
                "td": (self._model_pso.td_min, self._model_pso.td_max),
            }
        )

    def _get_pso_result_data(self) -> DynamicReportPsoResult:
        result = self._vm_evaluator.get_pso_result()
        return DynamicReportPsoResult(
            simulation_time=10.5,
            kp=10,
            ti=5,
            td=1,
            tf=0.01,
            recommended_sampling_rate=100,
            tf_limitation=None,
            error_criterion=0.15,
            overshoot_control=20.1,
            slew_rate_max=2,
            gain_margin=12,
            omega_180=4.5,
            phase_margin=50,
            omega_c=5.8,
            stability=2
        )
