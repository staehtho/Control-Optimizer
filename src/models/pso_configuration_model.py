import sys
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

    constraint: tuple[float, float] = (-5, 5)

    swarm_size: int = 40
    iterations: int = 14

    kp: tuple[float, float] = (0, 10)
    ti: tuple[float, float] = (sys.float_info.min, 10)
    td: tuple[float, float] = (0, 10)
