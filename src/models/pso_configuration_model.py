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
