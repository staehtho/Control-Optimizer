from dataclasses import dataclass

from app_domain.controlsys import ExcitationTarget, PerformanceIndex


@dataclass
class PsoConfigurationModel:
    t0: float = 0.0
    t1: float = 10.0

    excitation_target: ExcitationTarget = ExcitationTarget.REFERENCE
    error_criterion: PerformanceIndex = PerformanceIndex.ITAE

    kp_min: float = 0.0
    kp_max: float = 10.0
    ti_min: float = 1e-9
    ti_max: float = 10.0
    td_min: float = 0.0
    td_max: float = 10.0

    overshoot_control: float = 0.0
    overshoot_control_enabled: bool = True
    gain_margin: float = 0.0
    gain_margin_enabled: bool = True
    phase_margin: float = 0.0
    phase_margin_enabled: bool = True
    stability_margin: float = 0.0
    stability_margin_enabled: bool = True
