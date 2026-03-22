from __future__ import annotations
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot

from utils import LoggedProperty
from .base_viewmodel import BaseViewModel
from app_types import PlotData, PlotField, PlotLabels


class PlotViewModel(BaseViewModel):
    """ViewModel for plot settings and plot series data."""

    gridChanged = Signal()
    xMinChanged = Signal()
    xMaxChanged = Signal()
    dataChanged = Signal()

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._grid: bool = True
        self._x_min: float = 0.0
        self._x_max: float = 10.0
        self._data: dict[str, PlotData] = {}

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    # -------------------
    # grid
    # -------------------
    grid = LoggedProperty(
        path="_grid",
        signal="gridChanged",
        typ=bool,
    )

    # -------------------
    # x min
    # -------------------
    def _verify_x_min(self, value: float):

        result = self._validate_relation(
            value=value,
            other=self._x_max,
            relation="<",
            message=self.tr(
                "Invalid value: start ({x_min}) must be smaller than end ({x_max})."
            ).format(x_min=value, x_max=self._x_max)
        )

        return self._verify(PlotField.X_MIN, result)

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
                "Invalid value: end ({x_max}) must be greater than start ({x_min})."
            ).format(x_min=self._x_min, x_max=value)
        )

        return self._verify(PlotField.X_MAX, result)

    x_max = LoggedProperty(
        path="_x_max",
        signal="xMaxChanged",
        typ=float,
        custom_setter=_verify_x_max,
    )

    # -------------------
    # data
    # -------------------
    def get_data(self) -> dict[str, PlotData]:
        return {k: v for k, v in self._data.items()}

    @Slot(PlotData)
    def update_data(self, data: PlotData) -> None:
        current = self._data.get(data.key)
        if current is not None:
            # Keep user visibility selection across data refreshes.
            if not data.ignore_plot:
                data.show = current.show

        if current is None or current != data:
            self._data[data.key] = data
            self.logger.debug(f"Data updated for key '{data.key}'")
            self.dataChanged.emit()

    def retranslate_labels(self, translator: Callable[[PlotLabels], str]) -> None:
        """Update labels of all stored plot data."""
        for data in self._data.values():
            try:
                label_enum = PlotLabels(data.key)
            except ValueError:
                continue

            data.label = translator(label_enum)

        self.dataChanged.emit()

    @Slot(str, bool)
    def set_data_visibility(self, key: str, show: bool) -> None:
        data = self._data.get(key)
        if data is None or data.show == show:
            return
        data.show = show
        self.logger.debug(f"Visibility updated for key '{key}' -> {show}")
        self.dataChanged.emit()

    @Slot(str)
    def remove_data(self, key: str) -> None:
        if key in self._data:
            self._data.pop(key)
            self.logger.debug(f"Data removed for key '{key}'")
            self.dataChanged.emit()

    @Slot()
    def clear_data(self) -> None:
        if self._data:
            self._data.clear()
            self.logger.debug("All plot data cleared")
            self.dataChanged.emit()

