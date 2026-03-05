from dataclasses import dataclass, field
from typing import Any

from numpy import ndarray


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


@dataclass
class BodePlotData(PlotData):
    omega: list[float] | ndarray = field(default_factory=list)
    margin: list[float] | ndarray = field(default_factory=float)
    phase: list[float] | ndarray = field(default_factory=list)
