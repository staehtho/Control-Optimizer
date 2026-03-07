from enum import Enum


class FieldType(Enum):
    ...


class PlotField(FieldType):
    X_MIN = "x_min"
    X_MAX = "x_max"
