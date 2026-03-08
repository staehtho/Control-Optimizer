from utils import LoggedProperty
from .plot_viewmodel import PlotViewModel
from .types import ValidationResult, PlotField


class BodePlotViewModel(PlotViewModel):
    def __init__(self):
        super().__init__()

        self._x_min: float = 1e-2
        self._x_max: float = 1e5

    # -------------------
    # x min
    # -------------------
    def _verify_x_min(self, value: float):
        result = self._validate_relation(
            value=value,
            other=self._x_max,
            relation="<",
            message=self.tr(
                "Invalid value: omega min ({x_min}) must be smaller than omega max ({x_max})."
            ).format(x_min=f"{value:.1e}", x_max=f"{self._x_max:.1e}")
        )

        result_0 = self._validate_relation(
            value=value,
            other=0.0,
            relation=">",
            message=self.tr(
                "Invalid value: omega min ({value} must be greater than 0)"
            ).format(value=f"{value:.1e}")
        )

        return self._verify(PlotField.X_MIN, result) and self._verify(PlotField.X_MIN, result_0)

    x_min = LoggedProperty(
        path="_x_min",
        signal="xMinChanged",
        typ=float,
        custom_setter=_verify_x_min,
    )

    # -------------------
    # x max
    # -------------------
    def _verify_x_max(self, value: float):
        result = self._validate_relation(
            value=value,
            other=self._x_min,
            relation=">",
            message=self.tr(
                "Invalid value: omega max ({x_max}) must be greater than omega min ({x_min})."
            ).format(x_min=self._x_min, x_max=value)
        )

        result_0 = self._validate_relation(
            value=value,
            other=0.0,
            relation=">",
            message=self.tr(
                "Invalid value: omega max ({value} must be greater than 0)"
            ).format(value=f"{value:.1e}")
        )

        return self._verify(PlotField.X_MAX, result) and self._verify(PlotField.X_MAX, result_0)

    x_max = LoggedProperty(
        path="_x_max",
        signal="xMaxChanged",
        typ=float,
        custom_setter=_verify_x_max,
    )
