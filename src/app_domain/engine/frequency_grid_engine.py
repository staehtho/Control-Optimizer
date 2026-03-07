import logging
import numpy as np


class FrequencyGridEngine:
    """Engine for generating frequency grids for frequency-domain analysis.

    This engine generates a logarithmically spaced frequency vector
    ω ∈ [w_min, w_max] suitable for Bode, Nyquist, or sensitivity plots
    and provides utilities to computeBode magnitude/phase from complex
    frequency responses.
    """

    def __init__(self) -> None:
        """Initialize the controller transfer engine."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FrequencyGridEngine initialized.")

    def compute(self, w_min: float, w_max: float, n: int = 1000) -> np.ndarray:
        """Generate a logarithmically spaced frequency vector.

        Args:
            w_min: Minimum frequency (rad/s), must be > 0.
            w_max: Maximum frequency (rad/s), must be > w_min.
            n: Number of frequency points to generate. Default is 1000.

        Returns:
            np.ndarray: Logarithmically spaced frequency vector of length n.
        """
        self._logger.info(
            "Generating frequency grid: w_min=%.3f, w_max=%.3f, n=%d",
            w_min,
            w_max,
            n
        )

        omega = np.logspace(np.log10(w_min), np.log10(w_max), n)

        self._logger.info(
            "Frequency grid generated (size=%d)", omega.size
        )

        return omega

    def bode_from_complex(self, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Convert a complex frequency response to Bode magnitude and phase.

        Args:
            y: Complex frequency response (e.g., L(s), G(s), or S(s)).

        Returns:
            Tuple[ndarray, ndarray]:
                - Magnitude in dB
                - Phase in degrees
        """
        self._logger.info("Computing Bode magnitude and phase (size=%d)", y.size)

        mag = 20 * np.log10(np.abs(y))
        phase = np.angle(y, deg=True)

        self._logger.info("Bode computation finished (mag.size=%d, phase.size=%d)", mag.size, phase.size)
        return mag, phase
