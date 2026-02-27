from typing import Callable

from PySide6.QtCore import QThread, Signal
import logging

from app_domain import PsoSimulationEngine, PsoSimulationParam, PsoResult


class PsoSimulationWorker(QThread):
    """Worker thread to execute PSO simulation asynchronously.

    This worker runs the PsoSimulationEngine in a background thread
    to avoid blocking the UI thread. When the computation finishes,
    the optimized PsoResult is emitted via the resultReady signal.
    """

    resultReady = Signal(PsoResult)

    def __init__(
            self,
            engine: PsoSimulationEngine,
            pso_simulation_param: PsoSimulationParam,
            callback_iteration_progress: Callable[[], None]
    ) -> None:
        """Initialize the worker.

        Args:
            engine: Domain-layer PSO simulation engine.
            pso_simulation_param: Parameter container for optimization.
            callback_iteration_progress: Callable that is executed after each
                PSO iteration. It is called once per completed iteration and
                can be used to update progress indicators or trigger UI updates.
        """
        super().__init__()

        self._engine = engine
        self._pso_simulation_param = pso_simulation_param
        self._callback_iteration_progress = callback_iteration_progress
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")

        self._logger.debug("PsoSimulationWorker initialized with parameters: %s", self._pso_simulation_param)

    def run(self) -> None:
        """Execute PSO simulation in background thread."""
        self._logger.info("PSO worker started.")
        result = self._engine.run_simulation(self._pso_simulation_param, callback=self._callback_iteration_progress)
        self._logger.info("PSO worker finished successfully.")
        self.resultReady.emit(result)
