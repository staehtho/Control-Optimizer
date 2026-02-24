from typing import Callable
import logging
from PySide6.QtCore import QThread, Signal
from numpy import ndarray

from app_domain import FunctionEngine


class FunctionWorker(QThread):
    """Worker thread to compute a function asynchronously (Infrastructure Layer).

    Attributes:
        resultReady: Signal emitting (t, y) when computation is finished.
    """

    resultReady = Signal(ndarray, ndarray)  # t, y

    def __init__(self, engine: FunctionEngine, t: ndarray, func: Callable[[ndarray], ndarray]) -> None:
        super().__init__()
        self._engine = engine
        self._t = t
        self._func = func
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("Worker initialized for t.size=%d", t.size)

    def run(self):
        """Run the function computation in a separate thread."""
        self._logger.info("Worker started function computation")
        y = self._engine.compute(self._t, self._func)
        self._logger.info("Worker finished function computation")
        self.resultReady.emit(self._t, y)
