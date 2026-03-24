from __future__ import annotations
from typing import TYPE_CHECKING
import logging

from PySide6.QtCore import QThread, Signal

from app_types import PlotLabels, FrequencyResponse

if TYPE_CHECKING:
    from numpy import ndarray
    from app_types import PlantTransferContext, ControllerTransferContext
    from app_domain.engine import (
        ControllerTransferEngine, FrequencyResponseEngine, FrequencyGridEngine, PlantTransferEngine
    )


class ClosedLoopFrequencyWorker(QThread):
    """Worker thread to compute frequency-domain responses of a closed-loop system.

    This worker computes the frequency vector, evaluates the plant and controller
    transfer functions, calculates open-loop, sensitivity, and complementary
    sensitivity functions, converts them to magnitude (dB) and phase (deg),
    and emits the results via the `resultReady` signal.

    Signals:
        resultReady (object): Emitted when the computation is complete.
    """

    resultReady = Signal(object)

    def __init__(
            self,
            plant_engine: PlantTransferEngine,
            controller_engine: ControllerTransferEngine,
            response_engine: FrequencyResponseEngine,
            frequency_engine: FrequencyGridEngine,
            context_plant: PlantTransferContext,
            context_controller: ControllerTransferContext,
            omega_min: float,
            omega_max: float
    ) -> None:
        """Initialize the ClosedLoopFrequencyWorker.

        Args:
            plant_engine: Engine to compute plant transfer function.
            controller_engine: Engine to compute controller transfer function.
            response_engine: Engine to compute open-loop, sensitivity, and complementary sensitivity.
            frequency_engine: Engine to generate frequency vector and convert complex responses to magnitude/phase.
            context_plant: Plant transfer context with coefficients.
            context_controller: Controller transfer context with PID parameters.
            omega_min: Minimum frequency (rad/s) for computation.
            omega_max: Maximum frequency (rad/s) for computation.
        """
        super().__init__()
        self._plant_engine = plant_engine
        self._controller_engine = controller_engine
        self._response_engine = response_engine
        self._frequency_engine = frequency_engine
        self._context_plant = context_plant
        self._context_controller = context_controller
        self._omega_min = omega_min
        self._omega_max = omega_max

        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(
            "ClosedLoopFrequencyWorker initialized (omega=[%.3f, %.3f])",
            omega_min, omega_max
        )

    def run(self) -> None:
        """Compute the frequency-domain responses and emit the results.

        Steps:
        1. Generate a logarithmic frequency vector.
        2. Compute plant and controller transfer functions at each frequency.
        3. Compute open-loop, sensitivity, and complementary sensitivity functions.
        4. Convert all complex responses to magnitude (dB) and phase (deg).
        5. Emit a `FrequencyResponse` via the `resultReady` signal.
        """
        self._logger.info(
            "Starting closed-loop frequency-domain computation for omega=[%.3f, %.3f]",
            self._omega_min, self._omega_max
        )

        # Generate frequency vector
        omega: ndarray = self._frequency_engine.compute(self._omega_min, self._omega_max)
        self._logger.debug("Frequency vector generated (size=%d)", omega.size)

        # Compute plant and controller transfer functions
        G: ndarray = self._plant_engine.compute(self._context_plant, omega)
        C: ndarray = self._controller_engine.compute(self._context_controller, omega)
        self._logger.debug("Plant and controller transfer functions computed (size=%d)", omega.size)

        # Compute open-loop, sensitivity, and complementary sensitivity
        L: ndarray = self._response_engine.open_loop(C, G)
        S: ndarray = self._response_engine.sensitivity(L)
        T: ndarray = self._response_engine.complementary_sensitivity(L)
        self._logger.debug("Open-loop, sensitivity, and complementary sensitivity computed")

        # Convert complex responses to magnitude and phase
        mag: dict[str, ndarray] = {}
        phase: dict[str, ndarray] = {}

        keys = [
            PlotLabels.C.value,
            PlotLabels.L.value,
            PlotLabels.S.value,
            PlotLabels.T.value,
        ]
        for key, value in zip(keys, [C, L, S, T]):
            mag[key], phase[key] = self._frequency_engine.bode_from_complex(value)
        self._logger.debug("Magnitude and phase computed for C, L, S, T")

        # Prepare dataclass and emit result
        result = FrequencyResponse(
            omega=omega,
            margin=mag,
            phase=phase,
        )

        self._logger.info("Closed-loop frequency-domain computation finished, emitting result")
        self.resultReady.emit(result)

