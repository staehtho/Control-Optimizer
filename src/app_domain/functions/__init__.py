from enum import Enum

from .base_function import BaseFunction
from .cosine_function import CosineFunction
from .sine_function import SineFunction
from .step_function import StepFunction


class FunctionTypes(Enum):
    STEP = StepFunction
    SINE = SineFunction
    COSINE = CosineFunction