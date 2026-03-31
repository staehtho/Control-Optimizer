from dataclasses import dataclass


@dataclass(frozen=True)
class PlotStyle:
    """Styling parameters used for matplotlib series rendering."""

    color: str
    plot_order: int
    linestyle: str = "-"
    marker: str = ""
    markersize: int = 0
    z_order: int = 10

    def mpl_kwargs(self) -> dict:
        """Return matplotlib keyword args for this style."""
        return {
            "color": self.color,
            "linestyle": self.linestyle,
            "marker": self.marker,
            "markersize": self.markersize,
        }
