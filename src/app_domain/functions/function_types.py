from enum import Enum

from ..functions.base_function import BaseFunction
from ..functions.browian_noise import BrownianNoise
from ..functions.cosine_function import CosineFunction
from ..functions.null_function import NullFunction
from ..functions.pink_noise import PinkNoise
from ..functions.rectangular_function import RectangularFunction
from ..functions.sine_function import SineFunction
from ..functions.step_function import StepFunction
from ..functions.white_noise import WhiteNoise


class FunctionTypes(Enum):
    NULL = NullFunction
    STEP = StepFunction
    SINE = SineFunction
    COSINE = CosineFunction
    RECTANGULAR = RectangularFunction

    BROWNIAN_NOISE = BrownianNoise
    PINK_NOISE = PinkNoise
    WHITE_NOISE = WhiteNoise


# Function types excluded from use as excitation targets
EXCLUDED_FUNCTION_TYPES: list[FunctionTypes] = [
    FunctionTypes.NULL,
    FunctionTypes.BROWNIAN_NOISE,
    FunctionTypes.PINK_NOISE,
    FunctionTypes.WHITE_NOISE
]

# ------------------------------------------------------------------
# Function Type Resolution
# ------------------------------------------------------------------
def resolve_function_type(function: BaseFunction) -> FunctionTypes:
    for func_type in FunctionTypes:
        if isinstance(function, func_type.value):
            return func_type

    raise ValueError(f"Function type {function} is not registered")
