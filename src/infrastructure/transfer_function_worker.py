from __future__ import annotations
from typing import TYPE_CHECKING
import logging

from PySide6.QtCore import QThread, Signal

from app_domain.controlsys import Plant
from app_types import PlotLabels, FrequencyResponse

if TYPE_CHECKING:
    from numpy import ndarray
    from app_types import PlantTransferContext, ControllerTransferContext
    from app_domain.engine import (
        FrequencyResponseEngine, FrequencyGridEngine, PlantTransferEngine
    )


class TransferFunctionWorker(QThread):
    """
    Background worker for computing closed‑loop frequency responses.

    This thread assembles all components required for frequency‑domain
    analysis of a closed‑loop system: a plant model, a controller constructed
    from its specification context, and the engines responsible for frequency
    grid generation and complex response evaluation.

    The worker performs the entire computation asynchronously to keep the UI
    responsive. It generates the frequency vector, evaluates the plant and
    controller transfer functions, computes the open‑loop L(jω), sensitivity
    S(jω), and complementary sensitivity T(jω), converts all responses to
    magnitude (dB) and phase (deg), and finally emits a `FrequencyResponse`
    object via the `resultReady` signal.

    Signals:
        resultReady (FrequencyResponse):
            Emitted when all frequency‑domain quantities have been computed
            and packaged into a result object.
    """

    resultReady = Signal(object)

    def __init__(
            self,
            plant_engine: PlantTransferEngine,
            response_engine: FrequencyResponseEngine,
            frequency_engine: FrequencyGridEngine,
            context_plant: PlantTransferContext,
            context_controller: ControllerTransferContext,
            omega_min: float,
            omega_max: float
    ) -> None:
        """Initialize the TransferFunctionWorker.

        Args:
            plant_engine: Engine to compute plant transfer function.
            response_engine: Engine to compute open-loop, sensitivity, and complementary sensitivity.
            frequency_engine: Engine to generate frequency vector and convert complex responses to magnitude/phase.
            context_plant: Plant transfer context with coefficients.
            context_controller: Controller transfer context with PID parameters.
            omega_min: Minimum frequency (rad/s) for computation.
            omega_max: Maximum frequency (rad/s) for computation.
        """
        super().__init__()
        self._plant_engine = plant_engine
        self._response_engine = response_engine
        self._frequency_engine = frequency_engine
        self._context_plant = context_plant
        self._context_controller = context_controller
        self._omega_min = omega_min
        self._omega_max = omega_max

        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(
            "TransferFunctionWorker initialized (omega=[%.3f, %.3f])",
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
        plant = Plant(self._context_plant.num, self._context_plant.den)
        cl = self._context_controller.controller(plant, **self._context_controller.controller_parmas)

        # Compute controller transfer functions
        C: ndarray = self._response_engine.compute(cl.controller, omega)
        self._logger.debug("Plant and controller transfer functions computed (size=%d)", omega.size)

        # Compute open-loop, sensitivity, and complementary sensitivity
        L: ndarray = self._response_engine.compute(cl.open_loop, omega)
        S: ndarray = self._response_engine.compute(cl.sensitivity, omega)
        T: ndarray = self._response_engine.compute(cl.closed_loop, omega)
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

