from dataclasses import dataclass

from app_domain.controlsys import AntiWindup


@dataclass
class ControllerModel:
    controller_type: str = "PID"

    constraint_min: float = -5.0
    constraint_max: float = 5.0

    anti_windup: AntiWindup = AntiWindup.CLAMPING
    ka: float = 1.0
    ka_enabled: bool = False
