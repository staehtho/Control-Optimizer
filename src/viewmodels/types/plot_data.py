from dataclasses import dataclass, field
from typing import Any

from numpy import ndarray, array_equal


@dataclass
class PlotData:
    key: str
    label: str
    plot_style: Any
    x: list[float] | ndarray = field(default_factory=list)
    y: list[float] | ndarray = field(default_factory=list)
    subplot_position: int = 1
    ignore_plot: bool = False
    show: bool = True

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PlotData):
            if not array_equal(other.x, self.x):
                return False

            if not array_equal(other.y, self.y):
                return False
            return True

        raise NotImplementedError



@dataclass
class BodePlotData(PlotData):
    omega: list[float] | ndarray = field(default_factory=list)
    margin: list[float] | ndarray = field(default_factory=float)
    phase: list[float] | ndarray = field(default_factory=list)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BodePlotData):
            if not array_equal(other.omega, self.omega):
                return False

            if not array_equal(other.margin, self.margin):
                return False

            if not array_equal(other.phase, self.phase):
                return False
            return True

        raise NotImplementedError
