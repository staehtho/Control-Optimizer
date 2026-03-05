from dataclasses import dataclass


@dataclass
class SimulationModel:
    t0: float = 0.0
    t1: float = 10.0
    kp: float = 0.0
    ti: float = 0.0
    td: float = 0.0
    tf: float = 0.0
