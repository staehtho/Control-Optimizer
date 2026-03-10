from dataclasses import dataclass
from enum import Enum

from .settings import ThemeType

class NavLabels(Enum):
    PLANT = "Plant"
    EXCITATION_FUNCTION = "Excitation Function"
    CONTROLLER = "Controller"
    PSO_PARAMETER = "PSO Parameter"
    EVALUATION = "Evaluation"
    SIMULATION = "Simulation"
    SETTINGS = "Settings"


@dataclass
class NavItem:
    key: NavLabels
    icons: dict[ThemeType, str]
    bottom: bool = False
