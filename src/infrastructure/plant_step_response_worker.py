from PySide6.QtCore import QThread, Signal
import logging
from numpy import ndarray

from app_domain import PlantStepResponseEngine
from app_domain.controlsys import MySolver


class PlantStepResponseWorker(QThread):
    """Worker thread to compute the step response asynchronously (Infrastructure Layer).

    Attributes:
        resultReady: Signal emitting (t, y) when computation finishes.
    """

    resultReady = Signal(ndarray, ndarray)

    def __init__(
            self,
            engine: PlantStepResponseEngine,
            num: list[float],
            den: list[float],
            t0: float,
            t1: float,
            solver: MySolver
    ) -> None:

        super().__init__()
        self._engine = engine
        self._num = num
        self._den = den
        self._t0 = t0
        self._t1 = t1
        self._solver = solver
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PlantStepResponseWorker initialized for t0=%.3f, t1=%.3f", t0, t1)

    def run(self):
        """Run the step response computation in a separate thread."""
        self._logger.info("Worker started step response computation")
        t, y = self._engine.compute(self._num, self._den, self._t0, self._t1, self._solver)
        self._logger.info("Worker finished step response computation")
        self.resultReady.emit(t, y)
