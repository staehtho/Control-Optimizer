from typing import Callable

from PySide6.QtCore import QThread, Signal
from numpy import ndarray

from app_domain import FunctionEngine


class FunctionWorker(QThread):
    """Worker thread to compute function asynchronously."""

    resultReady = Signal(ndarray, ndarray)  # t, y

    def __init__(self, engine: FunctionEngine, t: ndarray, func: Callable[[ndarray], ndarray]) -> None:
        super().__init__()
        self._engine = engine
        self._t = t
        self._func = func

    def run(self):
        y = self._engine.compute(self._t, self._func)
        self.resultReady.emit(self._t, y)