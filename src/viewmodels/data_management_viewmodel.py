from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from app_types import (
    DynamicReportData, DynamicReportPlant, DynamicReportExcitationFunction,
    DynamicReportControllerConfiguration, DynamicReportPsoConfiguration, DynamicReportPsoResult,
    DynamicReportBlockDiagram, DynamicReportTimeDomainPlot, DynamicReportBodePlot, DynamicReportTransferFunctions,
    PsoResult
)
from app_domain.functions import resolve_function_type
from resources.resources import OUTPUT_DIR, OutputFiles
from service.reporting import DynamicReport
from utils import LoggedProperty
from .evaluation_viewmodel import EvaluationViewModel
from .base_viewmodel import BaseViewModel
from views.translations import Translation

if TYPE_CHECKING:
    from app_domain import AppEngine
    from models import ModelContainer, DataManagementModel, PsoConfigurationModel, PsoSimulationSnapshot

BLOCK_DIAGRAM = "block_diagram"
TIME_DOMAIN = "time_domain"
FREQUENCY_DOMAIN = "frequency_domain"


class DataManagementViewModel(BaseViewModel):
    psoSimulationFinished = Signal()
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
    reportFailed = Signal(str)
    exportFinished = Signal()
    importFinished = Signal()

    def __init__(
            self,
            engine: AppEngine,
            vm_evaluator: EvaluationViewModel,
            model_container: ModelContainer,
            parent: QObject = None
    ) -> None:
        super().__init__(parent)

        self._engine = engine
        self._vm_evaluator = vm_evaluator
        self._model_data: DataManagementModel = model_container.model_data
        self._model_pso: PsoConfigurationModel = model_container.model_pso
        self._pending_snapshot: PsoSimulationSnapshot | None = None
        self._pending_result: PsoResult | None = None
        self._pending_svg_request: dict[str, str] | None = None
        self._report_path: Path = OUTPUT_DIR / "report.pdf"

        self._connect_signals()

    def _connect_signals(self) -> None:
        self._vm_evaluator.svgExportFinished.connect(self._on_svg_export_finished)
        self._vm_evaluator.psoSimulationFinished.connect(self._on_pso_simulation_finished)

    # ============================================================
    # Property
    # ============================================================
    include_plant: bool = LoggedProperty(
        path="_model_data.plant",
        signal="includePlantChanged",
        typ=bool,
    )

    include_excitation_function: bool = LoggedProperty(
        path="_model_data.excitation_function",
        signal="includeExcitationFunctionChanged",
        typ=bool,
    )

    include_controller_configuration: bool = LoggedProperty(
        path="_model_data.controller_configuration",
        signal="includeControllerConfigurationChanged",
        typ=bool,
    )

    include_pso_configuration: bool = LoggedProperty(
        path="_model_data.pso_configuration",
        signal="includePsoConfigurationChanged",
        typ=bool,
    )

    include_pso_result: bool = LoggedProperty(
        path="_model_data.pso_result",
        signal="includePsoResultChanged",
        typ=bool,
    )

    include_block_diagram: bool = LoggedProperty(
        path="_model_data.block_diagram",
        signal="includeBlockDiagramChanged",
        typ=bool,
    )

    include_time_domain_plot: bool = LoggedProperty(
        path="_model_data.time_domain_plot",
        signal="includeTimeDomainPlotChanged",
        typ=bool,
    )

    include_bode_plot: bool = LoggedProperty(
        path="_model_data.bode_plot",
        signal="includeBodePlotChanged",
        typ=bool,
    )

    include_transfer_functions: bool = LoggedProperty(
        path="_model_data.transfer_functions",
        signal="includeTransferFunctionsChanged",
        typ=bool,
    )

    # ============================================================
    # Pso finished
    # ============================================================
    @Slot()
    def _on_pso_simulation_finished(self) -> None:
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return

        result = self._vm_evaluator.get_pso_result()
        if result is None:
            return

        self._pending_snapshot = snapshot
        self._pending_result = result

        self.psoSimulationFinished.emit()

    # ============================================================
    # Report
    # ============================================================
    @Slot(str)
    def generate_report(self, path: str | Path) -> None:
        self._report_path = Path(path)
        if self._report_path.suffix.lower() != ".pdf":
            self._report_path = self._report_path.with_suffix(".pdf")

        self._pending_svg_request = {
            BLOCK_DIAGRAM: str(OUTPUT_DIR / OutputFiles.block_diagram),
            TIME_DOMAIN: str(OUTPUT_DIR / OutputFiles.time_domain_plot),
            FREQUENCY_DOMAIN: str(OUTPUT_DIR / OutputFiles.bode_plot),
        }
        if self._pending_svg_request is None:
            self.reportFailed.emit(self.tr("Failed to start report generation"))
            return
        self._vm_evaluator.request_save_svg(self._pending_svg_request)

    @Slot()
    def _on_svg_export_finished(self) -> None:

        if self._pending_snapshot is None or self._pending_result is None:
            self.reportFailed.emit(self.tr("Report generation failed due to missing data"))
            return

        self.logger.debug("Collecting report data...")

        report_data = DynamicReportData(
            plant_data=self._get_plant_data(self._pending_snapshot),
            excitation_function_data=self._get_excitation_function_data(self._pending_snapshot),
            controller_configuration_data=self._get_controller_configuration_data(self._pending_snapshot),
            pso_configuration_data=self._get_pso_configuration_data(self._pending_snapshot),
            pso_result_data=self._get_pso_result_data(self._pending_result),
            block_diagram_data=self._get_block_diagram_data(),
            time_domain_plot_data=self._get_time_domain_plot_data(),
            bode_plot_data=self._get_bode_plot_data(),
            transfer_functions_data=self._get_transfer_function_data(),
        )

        self.logger.debug("Create report")
        report = DynamicReport(str(self._report_path), self._model_data, report_data)
        report.build_report()

        self._pending_svg_request = None
        self.reportFinished.emit()

    # ============================================================
    # save / load project
    # ============================================================
    @Slot(str)
    def save_project(self, path: str | Path) -> None:
        self._engine.save_project(path)
        self.exportFinished.emit()

    @Slot(str)
    def load_project(self, path: str | Path) -> None:
        self._engine.load_project(path)
        self.importFinished.emit()

    # ============================================================
    # Internal Helper
    # ============================================================
    @staticmethod
    def _get_plant_data(snapshot: PsoSimulationSnapshot) -> DynamicReportPlant:
        return DynamicReportPlant(
            formula=r"G(s) = " + snapshot.plant_tf,
        )

    @staticmethod
    def _get_excitation_function_data(snapshot: PsoSimulationSnapshot) -> DynamicReportExcitationFunction:
        enum_tr = Translation()
        formula_desc = enum_tr(resolve_function_type(snapshot.excitation_function))

        return DynamicReportExcitationFunction(
            formula_desc=formula_desc,
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
            is_feasible=result.is_feasible,
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
