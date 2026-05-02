from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass

from app_domain.controlsys import AntiWindup

if TYPE_CHECKING:
    from app_domain.controlsys import ControllerType
    from app_types import ControllerSpec

@dataclass
class ControllerModel:
    controller_type: ControllerType
    controller_spec: ControllerSpec

    constraint_min: float = -5.0
    constraint_max: float = 5.0

    anti_windup: AntiWindup = AntiWindup.CLAMPING
    ka: float = 1.0
    ka_enabled: bool = False

    tuning_factor: float = 5.0
    sampling_rate: float | None = None
