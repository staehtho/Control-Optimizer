from PySide6.QtCore import QThread, Signal
from numpy import ndarray

from app_domain import PlantStepResponseEngine
from app_domain.controlsys import MySolver


class PlantStepResponseWorker(QThread):

    resultReady = Signal(ndarray, ndarray)  # t, y

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

    def run(self):
        t, y = self._engine.compute(
            self._num,
            self._den,
            self._t0,
            self._t1,
            self._solver,
        )
        self.resultReady.emit(t, y)