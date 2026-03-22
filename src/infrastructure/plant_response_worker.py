from __future__ import annotations
from typing import TYPE_CHECKING
import logging
from numpy import ndarray

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from app_domain.engine import PlantResponseEngine
    from app_types import PlantResponseContext


class PlantResponseWorker(QThread):
    """Background worker that computes a plant step response."""

    resultReady = Signal(ndarray, ndarray)

    def __init__(self, engine: PlantResponseEngine, context: PlantResponseContext) -> None:
        """Initialize worker dependencies and simulation inputs."""
        super().__init__()
        self._engine = engine
        self._context = context
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(
            "Initialized with t0=%.3f, t1=%.3f, num_order=%d, den_order=%d",
            context.t0,
            context.t1,
            max(len(context.num) - 1, 0),
            max(len(context.den) - 1, 0),
        )

    def run(self) -> None:
        """Run step-response simulation and emit ``resultReady``."""
        self._logger.info("Step-response worker started.")

        t, y = self._engine.compute(self._context)

        self._logger.info("Step-response worker finished (t.size=%d, y.size=%d).", t.size, y.size)
        self.resultReady.emit(t, y)

