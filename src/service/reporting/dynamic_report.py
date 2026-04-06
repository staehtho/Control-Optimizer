from __future__ import annotations
from typing import TYPE_CHECKING
from .base_report import BaseReport
from PySide6.QtCore import QCoreApplication
from .sections import (
    section_plant,
    section_function
)

if TYPE_CHECKING:
    from app_types import DynamicReportSections, DynamicReportData


class DynamicReport(BaseReport):

    def __init__(
        self,
        filename: str,
            sections: DynamicReportSections,
        data: DynamicReportData
    ) -> None:
        super().__init__(filename)
        self._sections = sections
        self._data = data

        self.header_text = QCoreApplication.translate("Report", "Control Optimizer")
        self.footer_text = QCoreApplication.translate("Report", "Page %d")


    def build_report(self) -> None:
        self.add_title(QCoreApplication.translate("Report", "Control Optimizer Report"))

        if self._sections.include_plant:
            section_plant(self, self._data.plant_data)

        if self._sections.include_function:
            section_function(self, self._data.function_data)

        self.build()
