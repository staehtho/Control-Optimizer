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
    progressChanged = Signal(int)

    def __init__(self, engine: PsoSimulationEngine, pso_simulation_param: PsoSimulationParam) -> None:
        """Initialize the worker.

        Args:
            engine: Domain-layer PSO simulation engine.
            pso_simulation_param: Parameter container for optimization.
        """
        super().__init__()

        self._engine = engine
        self._pso_simulation_param = pso_simulation_param
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")

        self._logger.debug("PsoSimulationWorker initialized with parameters: %s", self._pso_simulation_param)

    def run(self) -> None:
        """Execute PSO simulation in background thread."""
        self._logger.info("PSO worker started.")
        result = self._engine.run_simulation(self._pso_simulation_param, callback=self._on_iteration_progress)
        self._logger.info("PSO worker finished successfully.")
        self.resultReady.emit(result)

    def _on_iteration_progress(self, iteration: int):
        self.progressChanged.emit(iteration)
