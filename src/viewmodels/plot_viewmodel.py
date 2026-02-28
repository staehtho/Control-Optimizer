from typing import Sequence, Union

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from .base_viewmodel import BaseViewModel

NumberSeq = Union[Sequence[float], np.ndarray]


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
        self._data: dict[str, tuple[np.ndarray, np.ndarray]] = {}

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
    def get_data(self) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        return {k: (np.array(v[0]), np.array(v[1])) for k, v in self._data.items()}

    @Slot(str, tuple)
    def update_data(self, key: str, data: tuple[NumberSeq, NumberSeq]) -> None:
        x_arr = np.array(data[0])
        y_arr = np.array(data[1])

        current = self._data.get(key)
        if current is None or not (np.array_equal(current[0], x_arr) and np.array_equal(current[1], y_arr)):
            self._data[key] = (x_arr, y_arr)
            self.logger.debug(f"Data updated for key '{key}' (length {len(x_arr)})")
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
