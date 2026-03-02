from dataclasses import dataclass


@dataclass
class EvaluationModel:
    start_time: float = 0.0
    end_time: float = 10.0
    kp: float = 0.0
    ti: float = 0.0
    td: float = 0.0
    tf: float = 0.0
