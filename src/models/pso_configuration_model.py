from dataclasses import dataclass

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex


@dataclass
class PsoConfigurationModel:
    start_time: float = 0.0
    end_time: float = 1.0
    time_step: float = 1e-4

    anti_windup: AntiWindup = AntiWindup.CLAMPING
    excitation_target: ExcitationTarget = ExcitationTarget.REFERENCE
    performance_index: PerformanceIndex = PerformanceIndex.ITAE

    constraint_min: float = -5
    constraint_max: float = 5

    kp_min: float = 0
    kp_max: float = 10
    ti_min: float = 1e-9
    ti_max: float = 10
    td_min: float = 0
    td_max: float = 10
