import logging
from numpy import ndarray

from app_domain.controlsys import Plant, PIDClosedLoop
from app_types import ControllerTransferContext


class ControllerTransferEngine:
    """Domain engine for computing the controller transfer function.

    This engine evaluates the frequency response of the PID controller
    for a given set of controller parameters and frequency vector.

    The result is the complex controller transfer function:

        C(s)

    which can be used for further frequency-domain analysis such as
    open-loop, sensitivity, or Bode plots.
    """

    def __init__(self) -> None:
        """Initialize the controller transfer engine."""
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{id(self)}")
        self._logger.debug("ControllerTransferEngine initialized.")

    def compute(self, context: ControllerTransferContext, omega: ndarray) -> ndarray:
        """Compute the controller transfer function C(s).

        Args:
            context: Controller parameter configuration.
                Contains PID parameters such as Kp, Ti, Td, and Tf.
            omega: Frequency vector (rad/s) at which the controller
                transfer function should be evaluated.

        Returns:
            ndarray:
                Complex-valued controller frequency response C(s)
                evaluated at the given frequencies.
        """
        self._logger.info(
            "Starting controller transfer computation (Kp=%.3f, Ti=%.3f, Td=%.3f, Tf=%.3f, n=%d)",
            context.kp,
            context.ti,
            context.td,
            context.tf,
            omega.size,
        )

        # A default plant is required for PIDClosedLoop initialization,
        # but it is not used when computing the controller transfer function.
        pid_cl = PIDClosedLoop(
            Plant([1], [1, 1]),
            Kp=context.kp,
            Ti=context.ti,
            Td=context.td,
            Tf=context.tf,
        )

        s = 1j * omega
        C = pid_cl.controller(s)

        self._logger.info(
            "Controller transfer computation finished (omega.size=%d)",
            omega.size,
        )

        return C

