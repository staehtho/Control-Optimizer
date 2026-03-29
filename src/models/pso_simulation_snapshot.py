from dataclasses import dataclass

from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex
from app_domain.functions import BaseFunction


@dataclass(frozen=True)
class PsoSimulationSnapshot:
    plant_num: tuple[float, ...]
    plant_den: tuple[float, ...]
    plant_tf: str
    controller_anti_windup: AntiWindup
    controller_ka: float
    controller_constraint_min: float
    controller_constraint_max: float
    excitation_target: ExcitationTarget
    excitation_function: BaseFunction
    error_criterion: PerformanceIndex
