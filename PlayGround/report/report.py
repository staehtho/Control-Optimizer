from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex
from app_types import (
    DynamicReportData, DynamicReportPlant, DynamicReportExcitationFunction,
    DynamicReportControllerConfiguration, DynamicReportPsoConfiguration, DynamicReportPsoResult,
    DynamicReportBlockDiagram, DynamicReportTimeDomainPlot, DynamicReportBodePlot, DynamicReportTransferFunctions
)
from service.reporting import DynamicReport
from models import DataManagementModel

sections = DataManagementModel()

plant_data = DynamicReportPlant(
    formula=r"G(s) = \frac{(s - z_1)(s - z_2)\ldots}{(s - p_1)(s - p_2)\ldots}",
)

excitation_function_data = DynamicReportExcitationFunction(
    formula=r"u(t) = \lambda \cdot \sigma(t - t_0)",
    parameters={
        r"\lambda": 1.0,
        r"t_0": 0.0,
    }
)

controller_configuration_data = DynamicReportControllerConfiguration(
    controller_type="PID",
    anti_windup=AntiWindup.CLAMPING,
    factor_ka=1,
    constraint_min=-5,
    constraint_max=5,
    factor_n=5,
    min_sampling_rate=None
)

pso_configuration_data = DynamicReportPsoConfiguration(
    simulation_time=(0, 10),
    excitation_target=ExcitationTarget.REFERENCE,
    error_criterion=PerformanceIndex.ITAE,
    overshoot_control=5,
    slew_rate_max=2,
    slew_rate_window_size=10,
    gain_margin=10,
    phase_margin=60,
    stability=6,
    pso_bounds_parameters={
        "kp": (0, 10),
        "ti": (0, 10),
        "td": (0, 10),
    }
)

pso_result_data = DynamicReportPsoResult(
    is_feasible=False,
    simulation_time=10.5,
    kp=10,
    ti=5,
    td=1,
    tf=0.01,
    recommended_sampling_rate=100,
    tf_limitation=None,
    error_criterion=0.15,
    overshoot_control=20.1,
    slew_rate_max=2,
    gain_margin=12,
    omega_180=4.5,
    phase_margin=50,
    omega_c=5.8,
    stability_margin=2
)

block_diagram_data = DynamicReportBlockDiagram(
    block_diagram_svg="block_diagram.svg",
)

time_domain_data = DynamicReportTimeDomainPlot(
    plot_svg="system_response.svg"
)

bode_plot_data = DynamicReportBodePlot(
    plot_svg="bode_plot.svg",
)

transfer_function_data = DynamicReportTransferFunctions(
    plant="plant.svg",
    controller="controller.svg",
    open_loop="open_loop.svg",
    closed_loop="close_loop.svg",
    sensitivity="sensitivity.svg",
)

data = DynamicReportData(
    plant_data=plant_data,
    excitation_function_data=excitation_function_data,
    controller_configuration_data=controller_configuration_data,
    pso_configuration_data=pso_configuration_data,
    pso_result_data=pso_result_data,
    block_diagram_data=block_diagram_data,
    time_domain_plot_data=time_domain_data,
    bode_plot_data=bode_plot_data,
    transfer_functions_data=transfer_function_data,
)

report = DynamicReport("report.pdf", sections=sections, data=data)
report.build_report()
