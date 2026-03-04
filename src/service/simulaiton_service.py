from typing import Callable
import logging
from numpy import ndarray

from app_domain.engine import (
    PlantResponseEngine, PlantResponseContext, FunctionEngine, PsoSimulationEngine, PsoSimulationParam,
    PsoResult, ClosedLoopResponseEngine, ClosedLoopResponseContext
)
from app_domain.controlsys import MySolver
from infrastructure import PlantStepResponseWorker, FunctionWorker, PsoSimulationWorker, ClosedLoopResponseWorker


class SimulationService:
    """Application service that orchestrates asynchronous simulations.

    The service wires domain engines to Qt worker threads and exposes
    callback-based methods for ViewModels.
    """

    def __init__(self):
        """Initialize engines and worker slots used for async execution."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("SimulationService initialized.")
        self._step_engine = PlantResponseEngine()
        self._function_engine = FunctionEngine()
        self._pso_simulation_engine = PsoSimulationEngine()
        self._closed_loop_engine = ClosedLoopResponseEngine()
        # TODO: terminate Worker at closing
        self._step_worker = None
        self._function_workers: list[FunctionWorker] = []
        self._pso_simulation_worker = None
        self._closed_loop_worker = None

    def compute_step_response(
            self,
            context: PlantResponseContext,
            callback: Callable[[ndarray, ndarray], None],
    ) -> None:
        """Compute a step response asynchronously using a worker.

        Args:
            context: Plant simulation settings and disturbance signal
            callback: Function invoked with ``(t, y)`` when the worker completes.
        """
        if self._step_worker and self._step_worker.isRunning():
            self._logger.warning("StepResponseWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting StepResponseWorker for asynchronous computation")
        self._step_worker = PlantStepResponseWorker(self._step_engine, context)
        self._step_worker.resultReady.connect(callback)
        self._step_worker.start()

    def compute_function(
            self,
            t: ndarray,
            func: Callable[[ndarray], ndarray],
            callback: Callable[[ndarray, ndarray], None],
    ) -> None:
        """Compute a function asynchronously.

        Args:
            t: Input time vector.
            func: Callable mapping ``t -> y``.
            callback: Function invoked with ``(t, y)`` when the worker completes.
        """
        self._logger.info("Starting FunctionWorker for asynchronous computation")
        worker = FunctionWorker(self._function_engine, t, func)
        worker.resultReady.connect(callback)
        worker.finished.connect(lambda: self._on_function_worker_finished(worker))
        self._function_workers.append(worker)
        worker.start()

    def _on_function_worker_finished(self, worker: FunctionWorker) -> None:
        if worker in self._function_workers:
            self._function_workers.remove(worker)
        worker.deleteLater()

    def run_pso_simulation(
            self,
            pso_simulation_param: PsoSimulationParam,
            callback: Callable[[PsoResult], None],
            progress_callback: Callable[[int], None],
    ) -> None:
        """Run a PSO-based PID optimization asynchronously.

        Starts a ``PsoSimulationWorker`` in a background thread. Progress
        updates are forwarded after each completed iteration, and the final
        result is emitted via the completion callback. If a simulation is
        already running, the request is ignored.

        Args:
            pso_simulation_param: Full optimization configuration.
            callback: Function invoked with the final ``PsoResult``.
            progress_callback: Function invoked with the current iteration index.
        """
        if self._pso_simulation_worker and self._pso_simulation_worker.isRunning():
            self._logger.warning("PsoSimulationWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting PsoSimulationWorker for asynchronous computation")
        self._pso_simulation_worker = PsoSimulationWorker(self._pso_simulation_engine, pso_simulation_param)
        self._pso_simulation_worker.resultReady.connect(callback)
        self._pso_simulation_worker.progressChanged.connect(progress_callback)
        self._pso_simulation_worker.start()

    def compute_closed_loop_response(
            self,
            context: ClosedLoopResponseContext,
            callback: Callable[[ndarray, ndarray, ndarray], None],
    ) -> None:
        """Compute a closed-loop response asynchronously.

        Args:
            context: Closed-loop simulation inputs and disturbance signals.
            callback: Function invoked with ``(t, u, y)`` when the worker completes.
        """
        if self._closed_loop_worker and self._closed_loop_worker.isRunning():
            self._logger.warning("ClosedLoopResponseWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting ClosedLoopResponseWorker for asynchronous computation")
        self._closed_loop_worker = ClosedLoopResponseWorker(self._closed_loop_engine, context)
        self._closed_loop_worker.resultReady.connect(callback)
        self._closed_loop_worker.start()
