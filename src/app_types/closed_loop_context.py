from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from dataclasses import dataclass
import numpy as np

if TYPE_CHECKING:
    from app_domain.controlsys import AntiWindup, MySolver, ClosedLoop


@dataclass
class ClosedLoopResponseContext:
    """Input data required to compute a closed-loop time response."""

    num: list[float]
    den: list[float]

    controller: type[ClosedLoop]
    controller_params: dict[str, float]

    t0: float
    t1: float

    solver: MySolver

    anti_windup: AntiWindup
    ka: float
    constraint: tuple[float, float]

    reference: Callable[[np.ndarray], np.ndarray]
    input_disturbance: Callable[[np.ndarray], np.ndarray]
    measurement_disturbance: Callable[[np.ndarray], np.ndarray]
