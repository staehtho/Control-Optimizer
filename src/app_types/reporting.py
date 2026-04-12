from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex



@dataclass(frozen=True)
class DynamicReportData:
    plant_data: DynamicReportPlant
    excitation_function_data: DynamicReportExcitationFunction
    controller_configuration_data: DynamicReportControllerConfiguration
    pso_configuration_data: DynamicReportPsoConfiguration
    pso_result_data: DynamicReportPsoResult
    block_diagram_data: DynamicReportBlockDiagram
    time_domain_plot_data: DynamicReportTimeDomainPlot
    bode_plot_data: DynamicReportBodePlot
    transfer_functions_data: DynamicReportTransferFunctions


@dataclass(frozen=True)
class DynamicReportPlant:
    formula: str


@dataclass(frozen=True)
class DynamicReportExcitationFunction:
    formula: str
    parameters: dict[str, float]


@dataclass(frozen=True)
class DynamicReportControllerConfiguration:
    controller_type: str

    anti_windup: AntiWindup
    factor_ka: float | None

    constraint_min: float
    constraint_max: float

    factor_n: float
    min_sampling_rate: float | None


@dataclass(frozen=True)
class DynamicReportPsoConfiguration:
    simulation_time: tuple[float, float]
    excitation_target: ExcitationTarget

    error_criterion: PerformanceIndex
    overshoot_control: float | None
    slew_rate_max: float | None
    slew_rate_window_size: float | None

    gain_margin: float | None
    phase_margin: float | None
    stability: float | None

    pso_bounds_parameters: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class DynamicReportPsoResult:
    is_feasible: bool
    simulation_time: float
    kp: float
    ti: float
    td: float
    tf: float
    recommended_sampling_rate: float | None
    tf_limitation: str | None

    error_criterion: float
    overshoot_control: float | None
    slew_rate_max: float

    gain_margin: float
    omega_180: float
    phase_margin: float
    omega_c: float
    stability_margin: float


@dataclass(frozen=True)
class DynamicReportBlockDiagram:
    block_diagram_svg: str


@dataclass(frozen=True)
class DynamicReportTimeDomainPlot:
    plot_svg: str


@dataclass(frozen=True)
class DynamicReportBodePlot:
    plot_svg: str


@dataclass(frozen=True)
class DynamicReportTransferFunctions:
    plant: str
    controller: str
    open_loop: str
    closed_loop: str
    sensitivity: str
