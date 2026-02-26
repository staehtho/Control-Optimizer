from dataclasses import dataclass

from app_domain.controlsys import ExcitationTarget, PerformanceIndex


@dataclass
class PsoConfigurationModel:
    start_time: float = 0.0
    end_time: float = 1.0
    time_step: float = 1e-4

    excitation_target: ExcitationTarget = ExcitationTarget.REFERENCE
    performance_index: PerformanceIndex = PerformanceIndex.ITAE

    kp_min: float = 0
    kp_max: float = 10
    ti_min: float = 1e-9
    ti_max: float = 10
    td_min: float = 0
    td_max: float = 10
