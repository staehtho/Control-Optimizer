from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtCore import QCoreApplication

if TYPE_CHECKING:
    from .base_report import BaseReport


def section_pid_parameters(
    report: BaseReport,
    kp: float,
    ki: float,
    kd: float
) -> None:
    report.add_heading(QCoreApplication.translate("Report", "PID Parameters"))
    report.add_table(
        [
            [
                QCoreApplication.translate("Report", "Parameter"),
                QCoreApplication.translate("Report", "Value"),
            ],
            ["Kp", f"{kp}"],
            ["Ki", f"{ki}"],
            ["Kd", f"{kd}"],
        ]
    )


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
