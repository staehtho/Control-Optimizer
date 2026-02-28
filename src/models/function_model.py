from dataclasses import dataclass

from app_domain.functions import BaseFunction


@dataclass
class FunctionModel:
    selected_function: BaseFunction
