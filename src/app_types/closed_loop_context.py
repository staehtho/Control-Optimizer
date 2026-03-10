from dataclasses import dataclass
from typing import Callable
import numpy as np

from app_domain.controlsys import AntiWindup, MySolver


@dataclass
class ClosedLoopResponseContext:
    """Input data required to compute a closed-loop time response."""

    num: list[float]
    den: list[float]

    kp: float
    ti: float
    td: float
    tf: float

    t0: float
    t1: float

    solver: MySolver

    anti_windup: AntiWindup
    constraint: tuple[float, float]

    reference: Callable[[np.ndarray], np.ndarray]
    input_disturbance: Callable[[np.ndarray], np.ndarray]
    measurement_disturbance: Callable[[np.ndarray], np.ndarray]
