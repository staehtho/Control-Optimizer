from utils import LoggedProperty
from .plot_viewmodel import PlotViewModel


class BodePlotViewModel(PlotViewModel):
    def __init__(self):
        super().__init__()

        self._x_min: float = 1e-2
        self._x_max: float = 1e5

    # -------------------
    # x min
    # -------------------
    def _verify_x_min(self, value: float) -> bool:
        if value >= self._x_max:
            self.logger.warning(f"Attempted to set x_min >= x_max ({value} >= {self._x_max})")
            return False
        if value == 0.0:
            self.logger.warning(f"Attempted to set x_min 0 ({value} >= 0)")
            return False

        return True

    x_min = LoggedProperty(
        path="_x_min",
        signal="xMinChanged",
        typ=float,
        custom_setter=_verify_x_min,
    )
