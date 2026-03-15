from enum import Enum

from app_domain.functions import BaseFunction, StepFunction, SineFunction, CosineFunction, NullFunction, \
    RectangularFunction, WhiteNoise, BrownianNoise, PinkNoise


class FunctionTypes(Enum):
    NULL = NullFunction
    STEP = StepFunction
    SINE = SineFunction
    COSINE = CosineFunction
    RECTANGULAR = RectangularFunction

    BROWNIAN_NOISE = BrownianNoise
    PINK_NOISE = PinkNoise
    WHITE_NOISE = WhiteNoise


# ------------------------------------------------------------------
# Function Type Resolution
# ------------------------------------------------------------------
def resolve_function_type(function: BaseFunction) -> FunctionTypes:
    for func_type in FunctionTypes:
        if isinstance(function, func_type.value):
            return func_type

    raise ValueError(f"Function type {function} is not registered")
