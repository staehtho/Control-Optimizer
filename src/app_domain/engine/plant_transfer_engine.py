import logging
from numpy import ndarray

from app_domain.controlsys import Plant
from .types import PlantTransferContext


class PlantTransferEngine:
    """Domain engine for computing the plant transfer function.

    This engine evaluates the plant frequency response

        G(s)

    for a given plant model and frequency vector.
    """

    def __init__(self) -> None:
        """Initialize the plant transfer engine."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("PlantTransferEngine initialized.")

    def compute(self, context: PlantTransferContext, omega: ndarray) -> ndarray:
        """Compute the plant transfer function G(s).

        Args:
            context: Plant model parameters containing numerator and
                denominator coefficients of the transfer function.
            omega: Frequency vector (rad/s) at which the plant transfer
                function should be evaluated.

        Returns:
            ndarray:
                Complex-valued plant frequency response G(s) evaluated
                at the specified frequencies.
        """
        self._logger.info(
            "Starting plant transfer computation (num=%s, den=%s, n=%d)",
            context.num,
            context.den,
            omega.size,
        )

        plant = Plant(context.num, context.den)

        s = 1j * omega
        G = plant.system(s)

        self._logger.info(
            "Plant transfer computation finished (omega.size=%d)",
            omega.size,
        )

        return G
