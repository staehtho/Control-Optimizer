from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import logging
from PySide6.QtCore import QThread

if TYPE_CHECKING:
    from numpy import ndarray
    from app_types import (
        PlantResponseContext, PsoSimulationParam, PsoResult, ClosedLoopResponseContext, PlantTransferContext,
        FrequencyResponse, ControllerTransferContext
    )

    from infrastructure import (
        PlantResponseWorker, FunctionWorker, PsoSimulationWorker, ClosedLoopResponseWorker, PlantFrequencyWorker,
        ClosedLoopFrequencyWorker
    )


class SimulationService:
    """Application service that orchestrates asynchronous simulations.

    The service wires domain engines to Qt worker threads and exposes
    callback-based methods for ViewModels.
    """

    def __init__(self):
        """Initialize engines and worker slots used for async execution."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("SimulationService initialized.")
        self._plant_engine = None
        self._function_engine = None
        self._pso_simulation_engine = None
        self._closed_loop_engine = None
        self._frequency_grid_engine = None
        self._plant_transfer_engine = None
        self._controller_transfer_engine = None
        self._frequency_response_engine = None

        self._plant_workers: list[PlantResponseWorker] = []
        self._function_workers: list[FunctionWorker] = []
        self._pso_simulation_workers: list[PsoSimulationWorker] = []
        self._closed_loop_workers: list[ClosedLoopResponseWorker] = []
        self._plant_transfer_worker: PlantFrequencyWorker | None = None
        self._closed_loop_frequency_worker: ClosedLoopFrequencyWorker | None = None

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

        for worker in list(self._pso_simulation_workers):
            self._stop_worker(worker, f"PsoSimulationWorker[{id(worker)}]")
        self._pso_simulation_workers.clear()

        for worker in list(self._closed_loop_workers):
            self._stop_worker(worker, f"ClosedLoopResponseWorker[{id(worker)}]")
        self._closed_loop_workers.clear()

        self._stop_worker(self._plant_transfer_worker, "PlantFrequencyWorker")
        self._plant_transfer_worker = None

        self._stop_worker(self._closed_loop_frequency_worker, "ClosedLoopFrequencyWorker")
        self._closed_loop_frequency_worker = None

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
        from infrastructure import PlantResponseWorker
        self._logger.info("Starting StepResponseWorker for asynchronous computation")

        if self._plant_engine is None:
            from app_domain.engine import PlantResponseEngine
            self._plant_engine = PlantResponseEngine()

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
        from infrastructure import FunctionWorker
        self._logger.info("Starting FunctionWorker for asynchronous computation")

        if self._function_engine is None:
            from app_domain.engine import FunctionEngine
            self._function_engine = FunctionEngine()

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
        from infrastructure import PsoSimulationWorker
        self._logger.info("Starting PsoSimulationWorker for asynchronous computation")

        if self._pso_simulation_engine is None:
            from app_domain.engine import PsoSimulationEngine
            self._pso_simulation_engine = PsoSimulationEngine()

        worker = PsoSimulationWorker(self._pso_simulation_engine, pso_simulation_param)
        worker.resultReady.connect(callback)
        worker.progressChanged.connect(progress_callback)
        worker.finished.connect(lambda w=worker: self._on_pso_worker_finished(w))
        self._pso_simulation_workers.append(worker)
        worker.start()

    def stop_pso_simulation(self) -> None:
        """Interrupt any running PSO simulation workers."""
        if not self._pso_simulation_workers:
            return
        self._logger.info("Interrupting PsoSimulationWorkers.")
        for worker in list(self._pso_simulation_workers):
            if not worker.isRunning():
                continue
            worker.requestInterruption()
            worker.quit()

    def _on_pso_worker_finished(self, worker: PsoSimulationWorker) -> None:
        if worker is None:
            return
        if worker in self._pso_simulation_workers:
            self._pso_simulation_workers.remove(worker)
        worker.deleteLater()

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
        from infrastructure import ClosedLoopResponseWorker
        self._logger.info("Starting ClosedLoopResponseWorker for asynchronous computation")

        if self._closed_loop_engine is None:
            from app_domain.engine import ClosedLoopResponseEngine
            self._closed_loop_engine = ClosedLoopResponseEngine()

        worker = ClosedLoopResponseWorker(self._closed_loop_engine, context)
        worker.resultReady.connect(callback)
        worker.finished.connect(lambda: self._on_closed_loop_worker_finished(worker))
        self._closed_loop_workers.append(worker)
        worker.start()

    def _on_closed_loop_worker_finished(self, worker: ClosedLoopResponseWorker) -> None:
        if worker in self._closed_loop_workers:
            self._closed_loop_workers.remove(worker)
        worker.deleteLater()

    def compute_plant_transfer_response(
            self,
            context: PlantTransferContext,
            omega_min: float,
            omega_max: float,
            callback: Callable[[FrequencyResponse], None],
    ) -> None:
        """Compute the plant frequency response asynchronously.

        This method starts a `PlantFrequencyWorker` in a background thread.
        It generates the frequency vector, computes the plant transfer function,
        converts it to magnitude and phase, and invokes the callback when done.

        If a previous worker is still running, the request is ignored.

        Args:
            context: Plant transfer context including numerator/denominator coefficients.
            omega_min: Minimum frequency (rad/s) for the computation.
            omega_max: Maximum frequency (rad/s) for the computation.
            callback: Function invoked with a `FrequencyResponse` result
                      when the worker completes.
        """
        from infrastructure import PlantFrequencyWorker
        if self._plant_transfer_worker and self._plant_transfer_worker.isRunning():
            self._logger.warning("PlantFrequencyWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting PlantFrequencyWorker for asynchronous plant Bode computation")

        if self._plant_transfer_engine is None:
            from app_domain.engine import PlantTransferEngine
            self._plant_transfer_engine = PlantTransferEngine()

        if self._frequency_grid_engine is None:
            from app_domain.engine import FrequencyGridEngine
            self._frequency_grid_engine = FrequencyGridEngine()

        # Create and start the worker
        self._plant_transfer_worker = PlantFrequencyWorker(
            self._plant_transfer_engine,
            self._frequency_grid_engine,
            context,
            omega_min,
            omega_max
        )
        self._plant_transfer_worker.resultReady.connect(callback)
        self._plant_transfer_worker.start()

    def compute_closed_loop_transfer_response(
            self,
            context_plant: PlantTransferContext,
            context_control: ControllerTransferContext,
            omega_min: float,
            omega_max: float,
            callback: Callable[[FrequencyResponse], None],
    ) -> None:
        """Compute the closed-loop frequency-domain response asynchronously.

        This method starts a `ClosedLoopFrequencyWorker` in a background thread.
        It generates the frequency vector, computes plant and controller transfer
        functions, calculates open-loop, sensitivity, and complementary sensitivity,
        converts all results to magnitude and phase, and invokes the callback when done.

        If a previous worker is still running, the request is ignored.

        Args:
            context_plant: Plant transfer context including numerator/denominator coefficients.
            context_control: Controller transfer context including PID parameters.
            omega_min: Minimum frequency (rad/s) for the computation.
            omega_max: Maximum frequency (rad/s) for the computation.
            callback: Function invoked with a `FrequencyResponse`
                      when the worker completes.
        """
        from infrastructure import ClosedLoopFrequencyWorker
        if self._closed_loop_frequency_worker and self._closed_loop_frequency_worker.isRunning():
            self._logger.warning("ClosedLoopFrequencyWorker is busy. Ignoring request.")
            return

        self._logger.info("Starting ClosedLoopFrequencyWorker for asynchronous closed-loop Bode computation")

        if self._plant_transfer_engine is None:
            from app_domain.engine import PlantTransferEngine
            self._plant_transfer_engine = PlantTransferEngine()

        if self._controller_transfer_engine is None:
            from app_domain.engine import ControllerTransferEngine
            self._controller_transfer_engine = ControllerTransferEngine()

        if self._frequency_response_engine is None:
            from app_domain.engine import FrequencyResponseEngine
            self._frequency_response_engine = FrequencyResponseEngine()

        if self._frequency_grid_engine is None:
            from app_domain.engine import FrequencyGridEngine
            self._frequency_grid_engine = FrequencyGridEngine()

        # Create and start the worker
        self._closed_loop_frequency_worker = ClosedLoopFrequencyWorker(
            self._plant_transfer_engine,
            self._controller_transfer_engine,
            self._frequency_response_engine,
            self._frequency_grid_engine,
            context_plant,
            context_control,
            omega_min,
            omega_max
        )
        self._closed_loop_frequency_worker.resultReady.connect(callback)
        self._closed_loop_frequency_worker.start()

