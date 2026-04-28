from dataclasses import dataclass
from typing import List

from numpy import ndarray

from app_domain.controlsys import ClosedLoop


@dataclass(frozen=True)
class PlantTransferContext:
    """Input parameters for computing the plant frequency response.

    This context provides the necessary information to evaluate the plant's
    transfer function G(s) in the frequency domain.

    Attributes:
        num: Numerator coefficients of the plant transfer function.
        den: Denominator coefficients of the plant transfer function.
    """
    num: List[float]
    den: List[float]


@dataclass(frozen=True)
class FrequencyResponse:
    """Frequency-domain response for one or more transfer functions.

    This dataclass stores the results of Bode computations for a plant,
    controller, or closed-loop system. The magnitude and phase are stored
    in dictionaries to allow multiple responses (e.g., 'C', 'L', 'S', 'T')
    to be represented in a single object.

    Attributes:
        omega: Frequency vector (rad/s) at which the responses are evaluated.
        margin: Dictionary mapping transfer function names to their magnitude
                arrays in dB. Example keys: 'C', 'L', 'S', 'T'.
        phase: Dictionary mapping transfer function names to their phase arrays
               in degrees. Example keys: 'C', 'L', 'S', 'T'.
    """
    omega: ndarray
    margin: dict[str, ndarray]
    phase: dict[str, ndarray]


@dataclass(frozen=True)
class ControllerTransferContext:
    """Input parameters for computing the controller frequency response. """
    controller: type[ClosedLoop]
    controller_parmas: dict[str, float]
