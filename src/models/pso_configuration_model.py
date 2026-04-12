from dataclasses import dataclass

from app_domain.controlsys import ExcitationTarget, PerformanceIndex


@dataclass
class PsoConfigurationModel:
    t0: float = 0.0
    t1: float = 10.0

    excitation_target: ExcitationTarget = ExcitationTarget.REFERENCE

    kp_min: float = 0.0
    kp_max: float = 10.0
    ti_min: float = 0.001
    ti_max: float = 10.0
    td_min: float = 0.0
    td_max: float = 10.0

    error_criterion: PerformanceIndex = PerformanceIndex.ITAE
    overshoot_control: float = 10.0
    overshoot_control_enabled: bool = False
    slew_rate_max: float = 2.0
    slew_window_size: int = 10
    slew_rate_limit_enabled: bool = False
    gain_margin: float = 16.0
    gain_margin_enabled: bool = False
    phase_margin: float = 60.0
    phase_margin_enabled: bool = False
    stability_margin: float = 6.0
    stability_margin_enabled: bool = False
