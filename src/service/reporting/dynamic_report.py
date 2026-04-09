from __future__ import annotations
from typing import TYPE_CHECKING
from .base_report import BaseReport
from PySide6.QtCore import QCoreApplication
from .sections import (
    section_result_summary,
    section_plant,
    section_excitation_function,
    section_controller_configuration,
    section_pso_configuration,
    section_pso_result,
    section_block_diagram,
    section_time_domain,
    section_bode_plot,
    section_transfer_function
)

if TYPE_CHECKING:
    from app_types import DynamicReportData
    from models import DataManagementModel


class DynamicReport(BaseReport):

    def __init__(
        self,
        filename: str,
            sections: DataManagementModel,
        data: DynamicReportData
    ) -> None:
        super().__init__(filename)
        self._sections = sections
        self._data = data

        self.header_text = QCoreApplication.translate("Report", "Control Optimizer")
        self.footer_text = QCoreApplication.translate("Report", "Page %d")

    def build_report(self) -> None:
        self.add_title(QCoreApplication.translate("Report", "Control Optimizer Report"))

        section_result_summary(self, self._data.pso_result_data)

        if self._sections.plant:
            section_plant(self, self._data.plant_data)

        if self._sections.excitation_function:
            section_excitation_function(self, self._data.excitation_function_data)

        if self._sections.controller_configuration:
            section_controller_configuration(self, self._data.controller_configuration_data)

        if self._sections.pso_configuration:
            section_pso_configuration(self, self._data.pso_configuration_data)

        if self._sections.pso_result:
            section_pso_result(self, self._data.pso_configuration_data, self._data.pso_result_data)

        if self._sections.block_diagram:
            section_block_diagram(self, self._data.block_diagram_data)

        if self._sections.time_domain_plot:
            section_time_domain(self, self._data.time_domain_plot_data)

        if self._sections.bode_plot:
            section_bode_plot(self, self._data.bode_plot_data)

        if self._sections.transfer_functions:
            section_transfer_function(self, self._data.transfer_functions_data)

        self.build()
