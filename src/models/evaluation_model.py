from dataclasses import dataclass


@dataclass
class EvaluationModel:
    kp: float = 0.0
    ti: float = 0.0
    td: float = 0.0
    tf: float = 0.0
