from typing import Callable
import logging
from numpy import ndarray
from PySide6.QtCore import QThread

from app_domain.engine import PlantResponseEngine, FunctionEngine, PsoSimulationEngine, ClosedLoopResponseEngine
from app_domain.engine.types import PlantResponseContext, PsoSimulationParam, PsoResult, ClosedLoopResponseContext
from infrastructure import PlantResponseWorker, FunctionWorker, PsoSimulationWorker, ClosedLoopResponseWorker


class SimulationService:
    """Application service that orchestrates asynchronous simulations.

    The service wires domain engines to Qt worker threads and exposes
    callback-based methods for ViewModels.
    """

    def __init__(self):
        """Initialize engines and worker slots used for async execution."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("SimulationService initialized.")
        self._plant_engine = PlantResponseEngine()
        self._function_engine = FunctionEngine()
        self._pso_simulation_engine = PsoSimulationEngine()
        self._closed_loop_engine = ClosedLoopResponseEngine()

        self._plant_workers: list[PlantResponseWorker] = []
        self._function_workers: list[FunctionWorker] = []
        self._pso_simulation_worker = None
        self._closed_loop_workers: list[ClosedLoopResponseWorker] = []

    def _stop_worker(self, worker: QThread | None, name: str, timeout_ms: int = 2000) -> None:
        """Try graceful stop first, then force terminate as a last resort."""
        if worker is None or not worker.isRunning():
            return

        self._logger.info("Stopping %s...", name)
        worker.requestInterruption()
        worker.quit()

        if worker.wait(timeout_ms):
            self._logger.info("%s stopped gracefully.", name)
            return

        self._logger.warning("%s did not stop in time; forcing terminate().", name)
        worker.terminate()
        worker.wait()

    def shutdown(self) -> None:
        """Stop all running simulation workers during application shutdown."""
        self._logger.info("SimulationService shutdown started.")

        for worker in list(self._plant_workers):
            self._stop_worker(worker, f"PlantResponseWorker[{id(worker)}]")
        self._plant_workers.clear()

        for worker in list(self._function_workers):
            self._stop_worker(worker, f"FunctionWorker[{id(worker)}]")
        self._function_workers.clear()

        self._stop_worker(self._pso_simulation_worker, "PsoSimulationWorker")
        self._pso_simulation_worker = None

        for worker in list(self._closed_loop_workers):
            self._stop_worker(worker, f"ClosedLoopResponseWorker[{id(worker)}]")
        self._closed_loop_workers.clear()

        self._logger.info("SimulationService shutdown finished.")

    def compute_plant_response(
            self,
            context: PlantResponseContext,
            callback: Callable[[ndarray, ndarray], None],
    ) -> None:
        """Compute a step response asynchronously using a worker.

        Args:
            context: Plant simulation settings and disturbance signal
            callback: Function invoked with ``(t, y)`` when the worker completes.
        """
        self._logger.info("Starting StepResponseWorker for asynchronous computation")
        worker = PlantResponseWorker(self._plant_engine, context)
        worker.resultReady.connect(callback)
        worker.finished.connect(lambda: self._on_step_worker_finished(worker))
        self._plant_workers.append(worker)
        worker.start()

    def _on_step_worker_finished(self, worker: PlantResponseWorker) -> None:
        if worker in self._plant_workers:
            self._plant_workers.remove(worker)
        worker.deleteLater()

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
        self._logger.info("Starting ClosedLoopResponseWorker for asynchronous computation")
        worker = ClosedLoopResponseWorker(self._closed_loop_engine, context)
        worker.resultReady.connect(callback)
        worker.finished.connect(lambda: self._on_closed_loop_worker_finished(worker))
        self._closed_loop_workers.append(worker)
        worker.start()

    def _on_closed_loop_worker_finished(self, worker: ClosedLoopResponseWorker) -> None:
        if worker in self._closed_loop_workers:
            self._closed_loop_workers.remove(worker)
        worker.deleteLater()
