from typing import Callable
import logging
from numpy import ndarray

from app_domain import PlantStepResponseEngine, FunctionEngine, PsoSimulationEngine, PsoSimulationParam
from app_domain.controlsys import MySolver
from infrastructure import PlantStepResponseWorker, FunctionWorker


class SimulationService:
    """Application service to orchestrate simulation computations.

    Handles asynchronous execution of Engines via Workers and
    provides a simple interface for ViewModels.
    """
    def __init__(self):
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("SimulationService initialized.")
        self._step_engine = PlantStepResponseEngine()
        self._function_engine = FunctionEngine()
        self._pso_simulation_engine = PsoSimulationEngine()

        self._step_worker = None
        self._function_worker = None
        self._pso_simulation_worker = None

    # Plant Step Response
    def compute_step_response(self, num: list[float], den: list[float], t0: float, t1: float, solver: MySolver, callback: Callable[[ndarray, ndarray], None]) -> None:
        """Compute a step response asynchronously using a worker.

        Args:
            num: Plant numerator coefficients.
            den: Plant denominator coefficients.
            t0: Start time.
            t1: End time.
            solver: Solver instance for simulation.
            callback: Callable to invoke with (t, y) when computation finishes.
        """
        if self._step_worker and self._step_worker.isRunning():
            self._logger.warning("StepResponseWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting StepResponseWorker for asynchronous computation")
        self._step_worker = PlantStepResponseWorker(self._step_engine, num, den, t0, t1, solver)
        self._step_worker.resultReady.connect(callback)
        self._step_worker.start()

    # Function computation
    def compute_function(self, t: ndarray, func: Callable[[ndarray], ndarray], callback: Callable[[ndarray, ndarray], None]) -> None:
        """Compute a function asynchronously.

        Args:
            t: Input time vector.
            func: Callable function mapping t -> y.
            callback: Callable to invoke with (t, y) when computation finishes.
        """
        if self._function_worker and self._function_worker.isRunning():
            self._logger.warning("FunctionWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting FunctionWorker for asynchronous computation")
        self._function_worker = FunctionWorker(self._function_engine, t, func)
        self._function_worker.resultReady.connect(callback)
        self._function_worker.start()

    def run_pso_simulation(self, pso_simulation_param: PsoSimulationParam, callback: Callable[[ndarray], None]) -> None:

        if self._pso_simulation_worker and self._pso_simulation_worker.isRunning():
            self._logger.warning("PsoSimulationWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting PsoSimulationWorker for asynchronous computation")
