import logging

from numpy import ndarray
from PySide6.QtCore import QThread, Signal

from app_domain.engine import ClosedLoopResponseContext, ClosedLoopResponseEngine


class ClosedLoopResponseWorker(QThread):
    """Background worker that computes a closed-loop response."""

    resultReady = Signal(ndarray, ndarray, ndarray)

    def __init__(self, engine: ClosedLoopResponseEngine, context: ClosedLoopResponseContext) -> None:
        """Initialize worker dependencies and closed-loop simulation context."""
        super().__init__()
        self._engine = engine
        self._context = context
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(
            "Initialized with t0=%.3f, t1=%.3f",
            context.t0, context.t1
        )

    def run(self) -> None:
        """Run closed-loop simulation and emit ``resultReady``."""
        self._logger.info("Closed-loop response worker started.")

        t, u, y = self._engine.compute(self._context)

        self._logger.info("Closed-loop response worker finished (size=%d).", t.size)
        self.resultReady.emit(t, u, y)
