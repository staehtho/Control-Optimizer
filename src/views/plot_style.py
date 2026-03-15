from dataclasses import dataclass
from collections.abc import Mapping

from app_types import PlotLabels


@dataclass(frozen=True)
class PlotStyle:
    color: str
    plot_order: int
    linestyle: str = "-"
    marker: str = ""
    markersize: int = 0
    z_order: int = 10

    def mpl_kwargs(self) -> dict:
        return {
            "color": self.color,
            "linestyle": self.linestyle,
            "marker": self.marker,
            "markersize": self.markersize,
        }


PLOT_STYLE: Mapping[PlotLabels, PlotStyle] = {
    PlotLabels.PLANT: PlotStyle("#7f7f7f", 1, z_order=14),
    PlotLabels.CLOSED_LOOP: PlotStyle("#1f77b4", 2, z_order=15),
    PlotLabels.REFERENCE: PlotStyle("#ff7f0e", 3, z_order=11),
    PlotLabels.INPUT_DISTURBANCE: PlotStyle("#2ca02c", 4, z_order=12),
    PlotLabels.MEASUREMENT_DISTURBANCE: PlotStyle("#d62728", 5, z_order=13),
    PlotLabels.CONTROL_SIGNAL: PlotStyle("#9467bd", 6, z_order=10),
    PlotLabels.FUNCTION: PlotStyle("#1f77b4", 7),

    PlotLabels.G: PlotStyle("#7f7f7f", 8, z_order=11),
    PlotLabels.C: PlotStyle("#ff7f0e", 9, z_order=12),
    PlotLabels.L: PlotStyle("#2ca02c", 10, z_order=13),
    PlotLabels.S: PlotStyle("#d62728", 11, z_order=14),
    PlotLabels.T: PlotStyle("#9467bd", 12, z_order=15),
}


