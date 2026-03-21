from dataclasses import dataclass

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex, MySolver
from app_domain.functions import BaseFunction


@dataclass
class PsoSimulationParam:
    """Parameter container for PSO-based PID optimization."""

    num: list[float]
    den: list[float]

    t0: float
    t1: float
    dt: float

    solver: MySolver

    anti_windup: AntiWindup
    constraint: tuple[float, float]

    excitation_target: ExcitationTarget
    function: BaseFunction
    error_criterion: PerformanceIndex

    kp: tuple[float, float]
    ti: tuple[float, float]
    td: tuple[float, float]

    swarm_size: int
    pso_iteration: int

    overshoot_control: float
    overshoot_control_enabled: bool
    gain_margin: float
    gain_margin_enabled: bool
    phase_margin: float
    phase_margin_enabled: bool
    stability_margin: float
    stability_margin_enabled: bool


@dataclass
class PsoResult:
    """Result container for optimized PID parameters."""

    simulation_time: float

    kp: float = 0
    ti: float = 0
    td: float = 0
    tf: float = 0

    t0: float = 0
    t1: float = 0
