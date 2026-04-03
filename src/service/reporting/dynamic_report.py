from __future__ import annotations
from .base_report import BaseReport
from PySide6.QtCore import QCoreApplication
from .sections import (
    section_pid_parameters,
    section_plot,
    section_notes,
    section_summary,
    section_block_diagram,
)
from dataclasses import dataclass

@dataclass
class DynamicReportSelection:
    include_pid: bool = False
    include_plot: bool = False
    include_block_diagram: bool = False
    include_notes: bool = False


@dataclass
class DynamicReportData:
    kp: float = 0.0
    ki: float = 0.0
    kd: float = 0.0
    svg_plot: str = ""
    svg_block_diagram: str = ""
    notes: str = ""


class DynamicReport(BaseReport):

    def __init__(
        self,
        filename: str,
        selection: DynamicReportSelection,
        data: DynamicReportData
    ) -> None:
        super().__init__(filename)
        self._selection = selection
        self._data = data

        self.header_text = QCoreApplication.translate("Report", "Control Optimizer")
        self.footer_text = QCoreApplication.translate("Report", "Page %d")


    def build_report(self) -> None:
        self.add_title(QCoreApplication.translate("Report", "Control Optimizer Report"))

        if self._selection.include_pid:
            section_pid_parameters(
                self,
                self._data.kp,
                self._data.ki,
                self._data.kd,
            )

        if self._selection.include_plot:
            svg_path = self._data.svg_plot
            if svg_path:
                section_plot(self, svg_path)

        if self._selection.include_block_diagram:
            svg_path = self._data.svg_block_diagram
            if svg_path:
                section_block_diagram(self, svg_path)

        if self._selection.include_notes:
            notes = self._data.notes
            section_notes(self, notes)

        # Always include summary
        section_summary(
            self,
            QCoreApplication.translate("Report", "This report was generated dynamically."),
        )

        self.build()
