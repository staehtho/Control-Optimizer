import logging

from numpy import ndarray
from PySide6.QtCore import QThread, Signal

from app_domain.engine import PlantStepResponseEngine
from app_domain.controlsys import MySolver


class PlantStepResponseWorker(QThread):
    """Background worker that computes a plant step response."""

    resultReady = Signal(ndarray, ndarray)

    def __init__(
            self,
            engine: PlantStepResponseEngine,
            num: list[float],
            den: list[float],
            t0: float,
            t1: float,
            solver: MySolver,
    ) -> None:
        """Initialize worker dependencies and simulation inputs."""
        super().__init__()
        self._engine = engine
        self._num = num
        self._den = den
        self._t0 = t0
        self._t1 = t1
        self._solver = solver
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(
            "Initialized with t0=%.3f, t1=%.3f, num_order=%d, den_order=%d",
            t0,
            t1,
            max(len(num) - 1, 0),
            max(len(den) - 1, 0),
        )

    def run(self) -> None:
        """Run step-response simulation and emit ``resultReady``."""
        self._logger.info("Step-response worker started.")

        t, y = self._engine.compute(self._num, self._den, self._t0, self._t1, self._solver)

        self._logger.info("Step-response worker finished (t.size=%d, y.size=%d).", t.size, y.size)
        self.resultReady.emit(t, y)
