from PySide6.QtCore import QThread, Signal
import logging
from numpy import ndarray

from app_domain.engine import ClosedLoopResponseEngine, ClosedLoopResponseContext


class ClosedLoopResponseWorker(QThread):
    resultReady = Signal(ndarray, ndarray)

    def __init__(self, engine: ClosedLoopResponseEngine, context: ClosedLoopResponseContext) -> None:
        super().__init__()

        self._engine = engine
        self._context = context
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")

        self._logger.debug("ClosedLoopResponseWorker initialized with parameters: %s", self._context)

    def run(self) -> None:
        """Execute PSO simulation in background thread."""
        self._logger.info("Closed-loop worker started.")
        t, y = self._engine.compute(self._context)
        self._logger.info("PSO worker finished successfully.")
        self.resultReady.emit(t, y)
