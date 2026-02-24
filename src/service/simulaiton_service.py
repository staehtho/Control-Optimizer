from typing import Callable

from numpy import ndarray

from app_domain import PlantStepResponseEngine, FunctionEngine
from app_domain.controlsys import MySolver
from infrastructure import PlantStepResponseWorker, FunctionWorker


class SimulationService:

    def __init__(self):
        self._step_engine = PlantStepResponseEngine()
        self._function_engine = FunctionEngine()
        self._step_worker = None
        self._function_worker = None

    # Plant Step Response
    def compute_step_response(self, num: list[float], den: list[float], t0: float, t1: float, solver: MySolver, callback: Callable[[ndarray, ndarray], None]) -> None:
        if self._step_worker and self._step_worker.isRunning():
            return
        self._step_worker = PlantStepResponseWorker(self._step_engine, num, den, t0, t1, solver)
        self._step_worker.resultReady.connect(callback)
        self._step_worker.start()

    # Function computation
    def compute_function(self, t: ndarray, func: Callable[[ndarray], ndarray], callback: Callable[[ndarray, ndarray], None]) -> None:
        if self._function_worker and self._function_worker.isRunning():
            return
        self._function_worker = FunctionWorker(self._function_engine, t, func)
        self._function_worker.resultReady.connect(callback)
        self._function_worker.start()