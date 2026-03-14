from enum import Enum

from app_domain.functions import BaseFunction, StepFunction, SineFunction, CosineFunction, NullFunction, \
    RectangularFunction


class FunctionTypes(Enum):
    NULL = NullFunction
    STEP = StepFunction
    SINE = SineFunction
    COSINE = CosineFunction
    RECTANGULAR = RectangularFunction


# ------------------------------------------------------------------
# Function Type Resolution
# ------------------------------------------------------------------
def resolve_function_type(function: BaseFunction) -> FunctionTypes:
    for func_type in FunctionTypes:
        if isinstance(function, func_type.value):
            return func_type

    raise ValueError(f"Function type {function} is not registered")
