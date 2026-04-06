from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtCore import QCoreApplication

if TYPE_CHECKING:
    from .base_report import BaseReport
    from app_types import DynamicReportPlant, DynamicReportFunction


def section_plant(report: BaseReport, data: DynamicReportPlant) -> None:
    report.add_heading(QCoreApplication.translate("Report", "Summary"))
    report.add_svg(data.formula_svg, height=32)


def section_function(report: BaseReport, data: DynamicReportFunction) -> None:
    report.add_heading(QCoreApplication.translate("Report", "Summary"))
    report.add_svg(data.formula_svg, height=32)
    header = [
        QCoreApplication.translate("Report", "Parameter"),
        QCoreApplication.translate("Report", "Value"),
    ]
    table_data = [[{"latex": param}, str(value)] for param, value in data.parameters.items()]
    report.add_table(header, table_data)


def section_plot(report: BaseReport, svg_path: str) -> None:
    report.add_heading(QCoreApplication.translate("Report", "System Response Plot"))
    report.add_svg(svg_path)


def section_block_diagram(report: BaseReport, svg_path: str) -> None:
    report.add_heading(QCoreApplication.translate("Report", "System Response Plot"))
    report.add_svg(svg_path)


def section_notes(report: BaseReport, text: str) -> None:
    report.add_heading(QCoreApplication.translate("Report", "User Notes"))
    report.add_paragraph(text)


def section_summary(report: BaseReport, text: str) -> None:
    report.add_heading(QCoreApplication.translate("Report", "Summary"))
    report.add_paragraph(text)
