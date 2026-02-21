from PySide6.QtCore import QObject, Signal, Property, Slot
import numpy as np
import logging
from typing import Sequence, Dict, Tuple, Union

NumberSeq = Union[Sequence[float], np.ndarray]

from .baseViewModel import BaseViewModel

class PlotViewModel(BaseViewModel):
    """
    ViewModel for managing plot data and properties in a Qt MVVM setup.

    Attributes:
        grid (bool): Whether to show the grid in the plot.
        start_time (float): Start time for the plot range.
        end_time (float): End time for the plot range.
        _data (dict): Dictionary storing plot data in the form {label: (x_values, y_values)}.

    Signals:
        gridChanged: Emitted when the grid visibility changes.
        startTimeChanged: Emitted when start_time changes.
        endTimeChanged: Emitted when end_time changes.
        dataChanged: Emitted when any plot data is updated or removed.
    """

    gridChanged = Signal()
    startTimeChanged = Signal()
    endTimeChanged = Signal()
    dataChanged = Signal()

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._grid: bool = True
        self._start_time: float = 0.0
        self._end_time: float = 10.0
        self._data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

        self._logger.setLevel(logging.DEBUG)  # You can adjust the level
        if not self._logger.hasHandlers():
            # Add default console handler if none exists
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
            self._logger.addHandler(ch)

    # ----------------------
    # Grid Property
    # ----------------------
    def _get_grid(self) -> bool:
        return self._grid

    def _set_grid(self, value: bool) -> None:
        if value != self._grid:
            self._grid = value
            self._logger.debug(f"Grid visibility set to {value}")
            self.gridChanged.emit()

    grid = Property(bool, _get_grid, _set_grid, notify=gridChanged) # type: ignore[assignment]

    # ----------------------
    # Start Time Property
    # ----------------------
    def _get_start_time(self) -> float:
        return self._start_time

    def _set_start_time(self, value: float) -> None:
        if value >= self._end_time:
            self._logger.warning(f"Attempted to set start_time >= end_time ({value} >= {self._end_time})")
            return
        if value != self._start_time:
            self._start_time = value
            self._logger.debug(f"start_time set to {value}")
            self.startTimeChanged.emit()

    start_time = Property(float, _get_start_time, _set_start_time, notify=startTimeChanged) # type: ignore[assignment]

    # ----------------------
    # End Time Property
    # ----------------------
    def _get_end_time(self) -> float:
        return self._end_time

    def _set_end_time(self, value: float) -> None:
        if value <= self._start_time:
            self._logger.warning(f"Attempted to set end_time <= start_time ({value} <= {self._start_time})")
            return
        if value != self._end_time:
            self._end_time = value
            self._logger.debug(f"end_time set to {value}")
            self.endTimeChanged.emit()

    end_time = Property(float, _get_end_time, _set_end_time, notify=endTimeChanged) # type: ignore[assignment]

    # ----------------------
    # Data Management
    # ----------------------
    def get_data(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        return {k: (np.array(v[0]), np.array(v[1])) for k, v in self._data.items()}

    @Slot(str, tuple)
    def update_data(self, key: str, data: Tuple[NumberSeq, NumberSeq]) -> None:
        x_arr = np.array(data[0])
        y_arr = np.array(data[1])

        current = self._data.get(key)
        if current is None or not (np.array_equal(current[0], x_arr) and np.array_equal(current[1], y_arr)):
            self._data[key] = (x_arr, y_arr)
            self._logger.debug(f"Data updated for key '{key}' (length {len(x_arr)})")
            self.dataChanged.emit()

    @Slot(str)
    def remove_data(self, key: str) -> None:
        if key in self._data:
            self._data.pop(key)
            self._logger.debug(f"Data removed for key '{key}'")
            self.dataChanged.emit()

    @Slot()
    def clear_data(self) -> None:
        if self._data:
            self._data.clear()
            self._logger.debug("All plot data cleared")
            self.dataChanged.emit()