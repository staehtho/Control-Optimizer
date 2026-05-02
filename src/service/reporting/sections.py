from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6.QtCore import QCoreApplication

from app_domain.controlsys import AntiWindup
from utils import format_value
from views.translations import Translation

if TYPE_CHECKING:
    from .base_report import BaseReport
    from app_types import (
        DynamicReportPlant, DynamicReportExcitationFunction, DynamicReportControllerConfiguration,
        DynamicReportPsoConfiguration, DynamicReportPsoResult, DynamicReportBlockDiagram, DynamicReportTimeDomainPlot,
        DynamicReportBodePlot, DynamicReportTransferFunctions
    )

TRANSLATION = Translation()


def section_result_summary(report: BaseReport, data: DynamicReportPsoResult) -> None:
    if not data.is_feasible:
        report.add_paragraph(
            QCoreApplication.translate(
                "Report",
                "Not feasible"  # TODO: better Text
            ),
            color="red",
            bold=True,
        )

    report.add_paragraph(
        QCoreApplication.translate(
            "Report",
            "PSO simulation finished after %(time)s seconds."
        ) % {
            "time": format_value(data.simulation_time, 3),
        }
    )
    report.add_paragraph(
        QCoreApplication.translate(
            "Report",
            "Controller Parameter: %(params)s."
        ) % {
            "params": ", ".join([f"{k.title()} = {format_value(v, 3)}" for k, v in data.controller_params.items()])
        }
    )


def section_plant(report: BaseReport, data: DynamicReportPlant) -> None:
    with report.section():
        report.add_heading(QCoreApplication.translate("Report", "Plant Model"))
        report.add_paragraph(
            QCoreApplication.translate(
                "Report",
                "The plant is defined by the transfer function:"
            )
        )
        report.add_latex(data.formula, height=25)

def section_excitation_function(report: BaseReport, data: DynamicReportExcitationFunction) -> None:
    with report.section():
        report.add_heading(QCoreApplication.translate("Report", "Excitation Function"))
        report.add_paragraph(
            QCoreApplication.translate(
                "Report",
                "The excitation function is a %(function)s:"
            ) % {"function": data.formula_desc}

        )
        report.add_latex(data.formula, height=25)
        report.add_paragraph(
            QCoreApplication.translate(
                "Report",
                "With the parameters:"
            )

        )
        header = [
            QCoreApplication.translate("Report", "Parameter"),
            QCoreApplication.translate("Report", "Value"),
        ]
        table_data = [[{"latex": param}, format_value(value, 3)] for param, value in data.parameters.items()]
        report.add_table(header, table_data, width=250)


def section_controller_configuration(report: BaseReport, data: DynamicReportControllerConfiguration) -> None:

    report.add_heading(QCoreApplication.translate("Report", "Controller Configuration"))

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Controller Type"))
        report.add_paragraph(
            QCoreApplication.translate(
                "Report",
                "%(type)s controller"
            ) % {"type": TRANSLATION(data.controller_type)}
        )

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Constraints"))
        report.add_itemize([
            QCoreApplication.translate(
                "Report",
                "Controller maximum output: %(max_output)s"
            ) % {"max_output": format_value(data.constraint_max, 3)},
            QCoreApplication.translate(
                "Report",
                "Controller minimum output: %(min_output)s"
            ) % {"min_output": format_value(data.constraint_min, 3)},
        ])

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Anti Windup"))
        base = TRANSLATION(data.anti_windup)

        ka_part = (
            QCoreApplication.translate("Report", " with Ka = %(ka)s")
            % {"ka": format_value(data.factor_ka, 3)}
            if data.anti_windup == AntiWindup.BACKCALCULATION or data.factor_ka is None
            else ""
        )

        str_anti_windup = QCoreApplication.translate(
            "Report",
            "%(anti_windup)s method%(ka_part)s."
        ) % {"anti_windup": base, "ka_part": ka_part}

        report.add_paragraph(str_anti_windup)

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Filter Time Constant"))
        report.add_paragraph(f"N = " + format_value(data.factor_n, 3))

        if data.min_sampling_rate is None:
            report.add_paragraph(
                QtCore.QCoreApplication.translate(
                    "Report",
                    "Sampling rate unknown."
                )
            )
        else:
            report.add_paragraph(
                QCoreApplication.translate(
                    "Report",
                    "Minimum sampling rate: %(sampling_rate)s"
                ) % {"sampling_rate": format_value(data.min_sampling_rate, 3) + " Hz"}
            )


def section_pso_configuration(report: BaseReport, data: DynamicReportPsoConfiguration) -> None:
    report.add_heading(QCoreApplication.translate("Report", "PSO Configuration"))

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Simulation Settings"))
        report.add_paragraph(
            QCoreApplication.translate(
                "Report",
                "Simulation time: %(t0)s-%(t1)s s"
            ) % {
                "t0": format_value(data.simulation_time[0], 3),
                "t1": format_value(data.simulation_time[1], 3),
            }
        )
        report.add_paragraph(
            QtCore.QCoreApplication.translate(
                "Report",
                "Excitation target: %(target)s"
            ) % {"target": TRANSLATION(data.excitation_target)}
        )

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Time Domain Targets"))
        report.add_itemize([
            QCoreApplication.translate(
                "Report",
                "Error criterion: %(error)s"
            ) % {"error": TRANSLATION(data.error_criterion)},
            QCoreApplication.translate(
                "Report",
                "Max Overshoot: %(max_overshoot)s %%"
            ) % {"max_overshoot": format_value(data.overshoot_control, 3)}
            if data.overshoot_control is not None
            else QCoreApplication.translate("Report", "Overshoot control is disabled."),
            QCoreApplication.translate(
                "Report",
                "Slew rate limitation maximum du/dt: %(max_du_dt)s with window size: %(window_size)s"
            ) % {
                "max_du_dt": format_value(data.slew_rate_max, 3),
                "window_size": format_value(data.slew_rate_window_size, 3)
            }
            if data.slew_rate_max is not None and data.slew_rate_window_size is not None
            else QCoreApplication.translate("Report", "Slew rate limitation is disabled."),
        ])

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Frequency Domain Targets"))
        report.add_itemize([
            QCoreApplication.translate(
                "Report",
                "Gain margin: %(gain_margin)s dB"
            ) % {"gain_margin": format_value(data.gain_margin, 3)}
            if data.gain_margin is not None
            else QCoreApplication.translate("Report", "Gain margin is disabled."),
            QCoreApplication.translate(
                "Report",
                "Phase margin: %(phase_margin)s°"
            ) % {"phase_margin": format_value(data.phase_margin, 3)}
            if data.phase_margin is not None
            else QCoreApplication.translate("Report", "Phase margin is disabled."),
            QCoreApplication.translate(
                "Report",
                "Stability margin: %(stability)s dB"
            ) % {"stability": format_value(data.stability, 3)}
            if data.stability is not None
            else QCoreApplication.translate("Report", "Stability margin is disabled."),
        ])

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "PSO Parameter Bounds"))
        header = [
            QCoreApplication.translate("Report", "Parameter"),
            QCoreApplication.translate("Report", "Min"),
            QCoreApplication.translate("Report", "Max"),
        ]
        table_data = [
            [param.title(), format_value(min_val, 3), format_value(max_val, 3)]
            for param, (min_val, max_val) in data.pso_bounds_parameters.items()
        ]
        report.add_table(header, table_data, width=250)


def section_pso_result(report: BaseReport, data_config: DynamicReportPsoConfiguration, data: DynamicReportPsoResult):
    report.add_heading(QCoreApplication.translate("Report", "PSO Result"))

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Optimized Controller Parameters"))
        header = [
            QCoreApplication.translate("Report", "Parameter"),
            QCoreApplication.translate("Report", "Value"),
        ]
        table_data = [[k.title(), format_value(v, 3)] for k, v in data.controller_params.items()]

        report.add_table(header, table_data, width=250)

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Sampling Rate"))

        if data.tf_limitation == "simulation":
            report.add_paragraph(
                QCoreApplication.translate(
                    "Report",
                    "Sampling rate was limited by simulation."
                )
            )
        elif data.tf_limitation == "sampling":
            report.add_paragraph(
                QCoreApplication.translate(
                    "Report",
                    "Sampling rate was limited by sampling rate."
                )
            )
        else:
            report.add_paragraph(
                QCoreApplication.translate(
                    "Report",
                    "Recommended sampling rate: %(sampling_rate)s Hz."
                ) % {"sampling_rate": format_value(data.recommended_sampling_rate, 3)}
            )

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Time Domain Characteristics"))
        header = [
            QCoreApplication.translate("Report", "Metric"),
            QCoreApplication.translate("Report", "Value"),
        ]
        table_data = [[TRANSLATION(data_config.error_criterion), format_value(data.error_criterion, 3)]]
        if data.overshoot_control is not None:
            table_data.append([
                QCoreApplication.translate("Report", "Maximum Overshoot"),
                format_value(data.overshoot_control, 3) + " %"
            ])
        table_data.extend([
            [
                QCoreApplication.translate("Report", "Slew Rate Limit du/dt"),
                format_value(data.slew_rate_max, 3)
            ],
        ])
        report.add_table(header, table_data, width=250)

    with report.section():
        report.add_subheading(QCoreApplication.translate("Report", "Frequency Domain Characteristics"))
        header = [
            QCoreApplication.translate("Report", "Metric"),
            QCoreApplication.translate("Report", "Value"),
        ]

        at_label = QCoreApplication.translate("Report", "at")

        table_data = [
            [
                QCoreApplication.translate("Report", "Gain margin"),
                f"{format_value(data.gain_margin, 3)} dB {at_label} {format_value(data.omega_180, 3)} rad/s"
            ],
            [
                QCoreApplication.translate("Report", "Phase margin"),
                f"{format_value(data.phase_margin, 3)}° {at_label} {format_value(data.omega_c, 3)} rad/s"
            ],
            [
                QCoreApplication.translate("Report", "Stability margin"),
                f"{format_value(data.stability_margin, 3)} dB"
            ],
        ]
        report.add_table(header, table_data, width=250)


def section_block_diagram(report: BaseReport, data: DynamicReportBlockDiagram):
    with report.section():
        report.add_heading(QCoreApplication.translate("Report", "Block Diagram"))
        report.add_svg(data.block_diagram_svg, width=500)


def section_time_domain(report: BaseReport, data: DynamicReportTimeDomainPlot):
    with report.section():
        report.add_heading(QCoreApplication.translate("Report", "Plot Time Domain"))
        report.add_svg(data.plot_svg, width=400)


def section_bode_plot(report: BaseReport, data: DynamicReportBodePlot):
    with report.section():
        report.add_heading(QCoreApplication.translate("Report", "Bode Plot"))
        report.add_svg(data.plot_svg, width=400)


def section_transfer_function(report: BaseReport, data: DynamicReportTransferFunctions):
    with report.section():
        report.add_heading(QCoreApplication.translate("Report", "Transfer Functions"))

        tf_data = [
            [QCoreApplication.translate("Report", "Plant"), data.plant],
            [QCoreApplication.translate("Report", "Controller"), data.controller],
            [QCoreApplication.translate("Report", "Open Loop"), data.open_loop],
            [QCoreApplication.translate("Report", "Closed Loop"), data.closed_loop],
            [QCoreApplication.translate("Report", "Sensitivity"), data.sensitivity],
        ]

        for subheading, formula in tf_data:
            report.add_subheading(subheading)
            report.add_latex(formula, height=25)
