import logging
from PySide6.QtCore import QThread, Signal
from numpy import ndarray

from app_domain.engine import PlantTransferEngine, FrequencyGridEngine
from app_domain.engine.types import PlantTransferContext, FrequencyResponse


class PlantFrequencyWorker(QThread):
    """Worker thread to compute the plant frequency response in a separate thread.

    This worker generates the frequency vector, computes the plant transfer
    function, converts it to magnitude and phase, and emits the results via
    the `resultReady` signal.

    Signals:
        resultReady (FrequencyResponse): Emitted when the computation is complete.
    """

    resultReady = Signal(FrequencyResponse)

    def __init__(
            self,
            engine: PlantTransferEngine,
            frequency_engine: FrequencyGridEngine,
            context: PlantTransferContext,
            omega_min: float,
            omega_max: float
    ) -> None:
        """Initialize the PlantFrequencyWorker.

        Args:
            engine: Engine to compute the plant transfer function.
            frequency_engine: Engine to generate the frequency vector and compute Bode conversion.
            context: Plant transfer context with coefficients and frequency range.
            omega_min: Minimum value of omega.
            omega_max: Maximum value of omega.
        """
        super().__init__()
        self._engine = engine
        self._frequency_engine = frequency_engine
        self._context = context
        self._omega_min = omega_min
        self._omega_max = omega_max
        self._logger = logging.getLogger(f"Worker.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(
            "PlantFrequencyWorker initialized (Plant num=%s, den=%s, omega=[%.3f, %.3f])",
            context.num, context.den, self._omega_min, self._omega_max
        )

    def run(self) -> None:
        """Compute the plant frequency response and emit the results.

        Steps:
        1. Generate the logarithmic frequency vector.
        2. Compute the plant transfer function at each frequency.
        3. Convert the complex response to magnitude (dB) and phase (deg).
        4. Emit a `FrequencyResponse` via the `resultReady` signal.
        """
        self._logger.info(
            "Starting plant frequency computation for omega=[%.3f, %.3f]",
            self._omega_min, self._omega_max
        )

        # Generate frequency vector
        omega: ndarray = self._frequency_engine.compute(
            self._omega_min,
            self._omega_max
        )
        self._logger.debug("Frequency vector generated (size=%d)", omega.size)

        # Compute plant transfer function
        G: ndarray = self._engine.compute(self._context, omega)
        self._logger.debug("Plant transfer function computed (size=%d)", G.size)

        # Convert to magnitude and phase
        mag_G, phase_G = self._frequency_engine.bode_from_complex(G)
        self._logger.debug(
            "Plant magnitude/phase computed (mag.size=%d, phase.size=%d)",
            mag_G.size, phase_G.size
        )

        # Prepare response dataclass
        from views.translations import PlotLabels
        result = FrequencyResponse(
            omega=omega,
            margin={PlotLabels.G.value: mag_G},
            phase={PlotLabels.G.value: phase_G}
        )

        self._logger.info("Plant frequency computation finished, emitting result")
        self.resultReady.emit(result)
