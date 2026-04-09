from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from app_types import (
    DynamicReportData, DynamicReportPlant, DynamicReportExcitationFunction,
    DynamicReportControllerConfiguration, DynamicReportPsoConfiguration, DynamicReportPsoResult,
    DynamicReportBlockDiagram, DynamicReportTimeDomainPlot, DynamicReportBodePlot, DynamicReportTransferFunctions,
    PsoResult
)
from resources.resources import OUTPUT_DIR, OutputFiles
from service.reporting import DynamicReport
from utils import LoggedProperty
from .evaluation_viewmodel import EvaluationViewModel
from .base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from models import ModelContainer, ReportModel, PsoConfigurationModel, PsoSimulationSnapshot


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
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return

        result = self._vm_evaluator.get_pso_result()
        if result is None:
            return
        # TODO: request svg: time domain bode and block diagram
        report_data = DynamicReportData(
            plant_data=self._get_plant_data(snapshot),
            excitation_function_data=self._get_excitation_function_data(snapshot),
            controller_configuration_data=self._get_controller_configuration_data(snapshot),
            pso_configuration_data=self._get_pso_configuration_data(snapshot),
            pso_result_data=self._get_pso_result_data(result),
            block_diagram_data=self._get_block_diagram_data(),
            time_domain_plot_data=self._get_time_domain_plot_data(),
            bode_plot_data=self._get_bode_plot_data(),
            transfer_functions_data=self._get_transfer_function_data(),
        )

        self.reportFinished.emit()

    # ============================================================
    # Internal Helper
    # ============================================================
    @staticmethod
    def _get_plant_data(snapshot: PsoSimulationSnapshot) -> DynamicReportPlant:
        return DynamicReportPlant(
            formula=snapshot.plant_tf,
        )

    @staticmethod
    def _get_excitation_function_data(snapshot: PsoSimulationSnapshot) -> DynamicReportExcitationFunction:
        return DynamicReportExcitationFunction(
            formula=snapshot.excitation_function.get_formula(),
            parameters=snapshot.excitation_function.get_param()
        )

    @staticmethod
    def _get_controller_configuration_data(snapshot: PsoSimulationSnapshot) -> DynamicReportControllerConfiguration:
        return DynamicReportControllerConfiguration(
            controller_type=snapshot.controller_type,
            anti_windup=snapshot.controller_anti_windup,
            factor_ka=snapshot.controller_ka,
            constraint_min=snapshot.controller_constraint_min,
            constraint_max=snapshot.controller_constraint_max,
            factor_n=snapshot.controller_tuning_factor,
            min_sampling_rate=snapshot.sampling_rate,
        )

    @staticmethod
    def _get_pso_configuration_data(snapshot: PsoSimulationSnapshot) -> DynamicReportPsoConfiguration:
        return DynamicReportPsoConfiguration(
            simulation_time=snapshot.simulation_time,
            excitation_target=snapshot.excitation_target,
            error_criterion=snapshot.error_criterion,
            overshoot_control=snapshot.overshoot_control if snapshot.overshoot_control_enabled else None,
            slew_rate_max=snapshot.slew_rate_max if snapshot.slew_rate_limit_enabled else None,
            slew_rate_window_size=snapshot.slew_window_size if snapshot.slew_rate_limit_enabled else None,
            gain_margin=snapshot.gain_margin if snapshot.gain_margin_enabled else None,
            phase_margin=snapshot.phase_margin if snapshot.phase_margin_enabled else None,
            stability=snapshot.stability_margin if snapshot.stability_margin_enabled else None,
            pso_bounds_parameters={
                "kp": snapshot.kp,
                "ti": snapshot.ti,
                "td": snapshot.td,
            }
        )

    @staticmethod
    def _get_pso_result_data(result: PsoResult) -> DynamicReportPsoResult:
        tf_limitation = None
        if result.tf_limited_sampling:
            tf_limitation = "sampling"
        elif result.tf_limited_simulation:
            tf_limitation = "simulation"

        return DynamicReportPsoResult(
            simulation_time=result.simulation_time,
            kp=result.kp,
            ti=result.ti,
            td=result.td,
            tf=result.tf,
            recommended_sampling_rate=result.min_sampling_rate,
            tf_limitation=tf_limitation,
            error_criterion=result.error_criterion,
            overshoot_control=result.overshoot if result.show_overshoot else None,
            slew_rate_max=result.slew_rate,
            gain_margin=result.gain_margin,
            omega_180=result.omega_180,
            phase_margin=result.phase_margin,
            omega_c=result.omega_c,
            stability_margin=result.stability_margin
        )

    @staticmethod
    def _get_block_diagram_data() -> DynamicReportBlockDiagram:
        return DynamicReportBlockDiagram(
            block_diagram_svg=OUTPUT_DIR / OutputFiles.block_diagram
        )

    @staticmethod
    def _get_time_domain_plot_data() -> DynamicReportTimeDomainPlot:
        return DynamicReportTimeDomainPlot(
            plot_svg=OUTPUT_DIR / OutputFiles.time_domain_plot
        )

    @staticmethod
    def _get_bode_plot_data() -> DynamicReportBodePlot:
        return DynamicReportBodePlot(
            plot_svg=OUTPUT_DIR / OutputFiles.bode_plot
        )

    def _get_transfer_function_data(self) -> DynamicReportTransferFunctions:
        tf = self._vm_evaluator.get_transfer_functions()
        return DynamicReportTransferFunctions(
            plant=tf.plant,
            controller=tf.controller,
            open_loop=tf.open_loop,
            closed_loop=tf.closed_loop,
            sensitivity=tf.sensitivity,
        )
