from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_report import BaseReport


def section_pid_parameters(
    report: BaseReport,
    kp: float,
    ki: float,
    kd: float
) -> None:
    report.add_heading("PID Parameters")
    report.add_table(
        [
            ["Parameter", "Value"],
            ["Kp", f"{kp}"],
            ["Ki", f"{ki}"],
            ["Kd", f"{kd}"],
        ]
    )


def section_plot(report: BaseReport, svg_path: str) -> None:
    report.add_heading("System Response Plot")
    report.add_svg(svg_path)


def section_notes(report: BaseReport, text: str) -> None:
    report.add_heading("User Notes")
    report.add_paragraph(text)


def section_summary(report: BaseReport, text: str) -> None:
    report.add_heading("Summary")
    report.add_paragraph(text)
