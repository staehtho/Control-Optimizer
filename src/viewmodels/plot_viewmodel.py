from __future__ import annotations
from typing import Callable, Iterable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app_types import PlotData, PlotField, PlotLabels
from resources.resources import TEMP_DIR
from utils import LoggedProperty
from .base_viewmodel import BaseViewModel


class PlotViewModel(BaseViewModel):
    """ViewModel for plot settings and plot series data."""

    gridChanged = Signal()
    xMinChanged = Signal()
    xMaxChanged = Signal()
    dataChanged = Signal()
    loadingChanged = Signal()

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._grid: bool = True
        self._x_min: float = 0.0
        self._x_max: float = 10.0
        self._data: dict[str, PlotData] = {}
        self._is_loading: bool = False
        self._loading_sources: int = 0

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
            valid=value < self._x_max,
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
            valid=value > self._x_min,
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

    is_loading = LoggedProperty(
        path="_is_loading",
        signal="loadingChanged",
        typ=bool,
        read_only=True,
    )

    @Slot(bool)
    def set_loading(self, is_loading: bool) -> None:
        if self._is_loading == is_loading:
            return

        self._is_loading = is_loading
        self.logger.debug("Plot loading state updated -> %s", is_loading)
        self.loadingChanged.emit()

    @Slot(bool)
    def track_loading(self, is_loading: bool) -> None:
        if is_loading:
            self._loading_sources += 1
        else:
            self._loading_sources = max(0, self._loading_sources - 1)

        self.set_loading(self._loading_sources > 0)

    @Slot(PlotData)
    def update_data(self, data: PlotData) -> None:
        if self._update_single_data(data):
            self.dataChanged.emit()

    def update_data_batch(self, data_items: Iterable[PlotData]) -> None:
        changed = False
        for data in data_items:
            changed = self._update_single_data(data) or changed

        if changed:
            self.dataChanged.emit()

    def _update_single_data(self, data: PlotData) -> bool:
        current = self._data.get(data.key)
        if current is not None:
            # Keep user visibility selection across data refreshes.
            if not data.ignore_plot:
                data.show = current.show

        if current is None or current != data:
            self._data[data.key] = data
            self.logger.debug(f"Data updated for key '{data.key}'")
            return True

        return False

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

    @Slot(str)
    def request_save_svg(self, file_name: str) -> None:
        candidate = Path(file_name)
        if candidate.name == file_name:
            path = Path(TEMP_DIR) / file_name
        else:
            path = candidate
        if path.suffix.lower() != ".svg":
            path = path.with_suffix(".svg")

        self.logger.debug("Save SVG requested -> %s", path)
        self.saveSvgRequested.emit(str(path))
