import logging
from numpy import ndarray


class FrequencyResponseEngine:
    """Engine for frequency-domain analysis of control systems.

    Provides utilities to compute open-loop transfer,
    sensitivity, and complementary sensitivity functions from complex
    frequency responses.
    """

    def __init__(self) -> None:
        """Initialize the frequency response engine with a logger."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("FrequencyResponseEngine initialized.")

    def open_loop(self, C: ndarray, G: ndarray) -> ndarray:
        """Compute the open-loop transfer function L = C * G.

        Args:
            C: Controller frequency response C(s)
            G: Plant frequency response G(s)

        Returns:
            ndarray: Open-loop transfer function L(s)
        """
        self._logger.info("Computing open-loop transfer function (size=%d)", C.size)
        L = C * G
        self._logger.info("Open-loop computation finished")
        return L

    def sensitivity(self, L: ndarray) -> ndarray:
        """Compute the sensitivity function S = 1 / (1 + L).

        Args:
            L: Open-loop transfer function L(s)

        Returns:
            ndarray: Sensitivity function S(s)
        """
        self._logger.info("Computing sensitivity function (size=%d)", L.size)
        S = 1 / (1 + L)
        self._logger.info("Sensitivity computation finished")
        return S

    def complementary_sensitivity(self, L: ndarray) -> ndarray:
        """Compute the complementary sensitivity function T = L / (1 + L).

        Args:
            L: Open-loop transfer function L(s)

        Returns:
            ndarray: Complementary sensitivity function T(s)
        """
        self._logger.info("Computing complementary sensitivity function (size=%d)", L.size)
        T = L / (1 + L)
        self._logger.info("Complementary sensitivity computation finished")
        return T

