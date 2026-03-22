from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import logging
from numpy import ndarray

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from app_domain.engine import FunctionEngine


class FunctionWorker(QThread):
    """Background worker that computes a function over a time vector."""

    resultReady = Signal(ndarray, ndarray)

    def __init__(self, engine: FunctionEngine, t: ndarray, func: Callable[[ndarray], ndarray]) -> None:
        """Initialize worker dependencies and function inputs."""
        super().__init__()
        self._engine = engine
        self._t = t
        self._func = func
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("Initialized with t.size=%d.", t.size)

    def run(self) -> None:
        """Compute the function values and emit ``resultReady``."""
        self._logger.info("Function worker started.")

        y = self._engine.compute(self._t, self._func)

        self._logger.info("Function worker finished (t.size=%d, y.size=%d).", self._t.size, y.size)
        self.resultReady.emit(self._t, y)
