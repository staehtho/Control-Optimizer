from dataclasses import dataclass, field

from services.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex


@dataclass
class PsoConfigurationModel:
    num: list[float] = field(default_factory=list)
    den: list[float] = field(default_factory=list)

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
    ti: tuple[float, float] = (0, 10)
    td: tuple[float, float] = (0, 10)
