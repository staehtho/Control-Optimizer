from dataclasses import dataclass
from collections.abc import Mapping

from views.translations import PlotLabels


@dataclass(frozen=True)
class PlotStyle:
    color: str
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
    PlotLabels.REFERENCE: PlotStyle("#ff7f0e", z_order=11),
    PlotLabels.INPUT_DISTURBANCE: PlotStyle("#2ca02c", z_order=12),
    PlotLabels.MEASUREMENT_DISTURBANCE: PlotStyle("#d62728", z_order=13),
    PlotLabels.PLANT: PlotStyle("#7f7f7f", z_order=14),
    PlotLabels.FUNCTION: PlotStyle("#1f77b4"),
    PlotLabels.CLOSED_LOOP: PlotStyle("#1f77b4", z_order=15),
    PlotLabels.CONTROL_SIGNAL: PlotStyle("#9467bd", z_order=10),
}
