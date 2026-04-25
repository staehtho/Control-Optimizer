from dataclasses import dataclass

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex, ControllerType
from app_domain.functions import BaseFunction


@dataclass(frozen=True)
class PsoSimulationSnapshot:
    plant_num: tuple[float, ...]
    plant_den: tuple[float, ...]
    plant_tf: str

    controller_type: ControllerType
    controller_anti_windup: AntiWindup
    controller_ka: float
    controller_constraint_min: float
    controller_constraint_max: float
    controller_tuning_factor: float
    sampling_rate: float | None

    simulation_time: tuple[float, float]
    excitation_target: ExcitationTarget
    excitation_function: BaseFunction
    error_criterion: PerformanceIndex

    bounds: tuple[list[float], list[float]]
    n_param: int

    overshoot_control: float
    overshoot_control_enabled: bool
    slew_rate_max: float
    slew_window_size: int
    slew_rate_limit_enabled: bool
    gain_margin: float
    gain_margin_enabled: bool
    phase_margin: float
    phase_margin_enabled: bool
    stability_margin: float
    stability_margin_enabled: bool
