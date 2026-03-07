from .plot_viewmodel import PlotViewModel
from .types import ValidationResult


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

    # -------------------
    # x min
    # -------------------
    def validate_x_min(self, value: float) -> ValidationResult:
        if value >= self._x_max:
            message = self.tr(
                "Invalid value: omega min ({x_min}) must be smaller than omega max ({x_max})."
            ).format(x_min=f"{value:.1e}", x_max=f"{self._x_max:.1e}")

            return ValidationResult(False, message)

        if value <= 0.0:
            message = self.tr(
                "Invalid value: omega min ({value} must be greater than 0)"
            ).format(value=f"{value:.1e}")

            return ValidationResult(False, message)

        return ValidationResult(True)

    # -------------------
    # x max
    # -------------------
    def validate_x_max(self, value: float) -> ValidationResult:
        if value <= self._x_min:
            message = self.tr(
                "Invalid value: omega max ({x_max}) must be greater than omega min ({x_min})."
            ).format(x_min=self._x_min, x_max=value)

            return ValidationResult(False, message)

        if value <= 0.0:
            message = self.tr(
                "Invalid value: omega max ({value} must be greater than 0)"
            ).format(value=f"{value:.1e}")

            return ValidationResult(False, message)

        return ValidationResult(True)
