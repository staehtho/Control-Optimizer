from dataclasses import dataclass, field

from app_domain.controlsys import ExcitationTarget, PerformanceIndex


@dataclass
class PsoConfigurationModel:
    t0: float = 0.0
    t1: float = 10.0

    excitation_target: ExcitationTarget = ExcitationTarget.REFERENCE

    min_bounds: dict[str, float] = field(default_factory=dict)
    lower_bounds: dict[str, float] = field(default_factory=dict)
    upper_bounds: dict[str, float] = field(default_factory=dict)
    n_params: int = 0

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
