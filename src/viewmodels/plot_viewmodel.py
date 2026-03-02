import numpy as np
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, Slot
from numba.core.typing.builtins import Bool

from .base_viewmodel import BaseViewModel


@dataclass
class PlotData:
    key: str
    label: str
    x: list[float] | np.ndarray
    y: list[float] | np.ndarray
    color: str
    order: int = 0
    ignore_plot: bool = False
    show: bool = True


class PlotViewModel(BaseViewModel):
    """ViewModel for plot settings and plot series data."""

    gridChanged = Signal()
    startTimeChanged = Signal()
    endTimeChanged = Signal()
    dataChanged = Signal()

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._grid: bool = True
        self._start_time: float = 0.0
        self._end_time: float = 10.0
        self._data: dict[str, PlotData] = {}

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    # -------------------
    # grid
    # -------------------
    grid = BaseViewModel._logged_property(
        attribute="_grid",
        notify_signal="gridChanged",
        property_type=bool,
    )

    # -------------------
    # start time
    # -------------------
    def _verify_start_time(self, value: float) -> bool:
        if value >= self._end_time:
            self.logger.warning(f"Attempted to set start_time >= end_time ({value} >= {self._end_time})")
            return False
        return True

    start_time = BaseViewModel._logged_property(
        attribute="_start_time",
        notify_signal="startTimeChanged",
        property_type=float,
        custom_setter=_verify_start_time,
    )

    # -------------------
    # end time
    # -------------------
    def _verify_end_time(self, value: float) -> bool:
        if value <= self._start_time:
            self.logger.warning(f"Attempted to set end_time <= start_time ({value} <= {self._start_time})")
            return False
        return True

    end_time = BaseViewModel._logged_property(
        attribute="_end_time",
        notify_signal="endTimeChanged",
        property_type=float,
        custom_setter=_verify_end_time,
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

        if current is None or not (np.array_equal(current.x, data.x) and np.array_equal(current.y, data.y)):
            self._data[data.key] = data
            self.logger.debug(f"Data updated for key '{data.key}' ({data})")
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
