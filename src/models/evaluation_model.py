from dataclasses import dataclass


@dataclass
class EvaluationModel:
    x_min: float = 0.0
    x_max: float = 10.0
    kp: float = 0.0
    ti: float = 0.0
    td: float = 0.0
    tf: float = 0.0
