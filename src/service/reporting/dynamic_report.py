from __future__ import annotations
from typing import Dict, Any
from .base_report import BaseReport
from .sections import (
    section_pid_parameters,
    section_plot,
    section_notes,
    section_summary,
)
from dataclasses import dataclass

@dataclass
class DynamicReportSelection:
    include_pid: bool
    include_plot: bool
    include_notes: bool


@dataclass
class DynamicReportData:
    kp: float
    ki: float
    kd: float
    svg_plot: str
    notes: str


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

    def build_report(self) -> None:
        self.add_title("PID Controller Report")

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

        if self._selection.include_notes:
            notes = self._data.notes
            section_notes(self, notes)

        # Always include summary
        section_summary(self, "This report was generated dynamically.")

        self.build()
