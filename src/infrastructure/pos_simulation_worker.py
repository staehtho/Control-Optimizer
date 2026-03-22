from __future__ import annotations
from typing import TYPE_CHECKING
import logging

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from app_domain.engine import PsoSimulationEngine
    from app_types import PsoSimulationParam


class PsoSimulationWorker(QThread):
    """Background worker that executes a PSO optimization run."""

    resultReady = Signal(object)
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

        if self.isInterruptionRequested():
            self._logger.info("PSO worker interrupted before start.")
            return

        try:
            result = self._engine.run_simulation(
                self._pso_simulation_param,
                callback=self._on_iteration_progress,
                should_stop=self.isInterruptionRequested,
            )
        except InterruptedError:
            self._logger.info("PSO worker interrupted.")
            return

        if self.isInterruptionRequested():
            self._logger.info("PSO worker interrupted after run.")
            return

        self._logger.info("PSO worker finished successfully.")
        self.resultReady.emit(result)

    def _on_iteration_progress(self, iteration: int) -> None:
        """Forward iteration progress from engine callback to Qt signal."""
        self.progressChanged.emit(iteration)

