import logging

from PySide6.QtCore import QThread, Signal

from app_domain.engine import PsoSimulationEngine
from app_domain.engine.types import PsoSimulationParam, PsoResult


class PsoSimulationWorker(QThread):
    """Background worker that executes a PSO optimization run."""

    resultReady = Signal(PsoResult)
    progressChanged = Signal(int)

    def __init__(self, engine: PsoSimulationEngine, pso_simulation_param: PsoSimulationParam) -> None:
        """Initialize worker dependencies and optimization parameters."""
        super().__init__()
        self._engine = engine
        self._pso_simulation_param = pso_simulation_param
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug("Initialized with parameters: %s", self._pso_simulation_param)

    def run(self) -> None:
        """Execute the optimization and emit ``resultReady`` when done."""
        self._logger.info("PSO worker started.")

        result = self._engine.run_simulation(
            self._pso_simulation_param,
            callback=self._on_iteration_progress,
        )

        self._logger.info("PSO worker finished successfully.")
        self.resultReady.emit(result)

    def _on_iteration_progress(self, iteration: int) -> None:
        """Forward iteration progress from engine callback to Qt signal."""
        self.progressChanged.emit(iteration)
