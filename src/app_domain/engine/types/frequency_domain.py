from dataclasses import dataclass
from typing import List

from numpy import ndarray


@dataclass
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


@dataclass
class PlantFrequencyResponse:
    """Frequency-domain response of a plant transfer function.

    This dataclass stores the results of a plant Bode computation,
    including the frequency vector, magnitude (in dB), and phase (in degrees).

    Attributes:
        omega: Frequency vector (rad/s) at which the response is evaluated.
        margin: Magnitude of the plant transfer function in dB.
        phase: Phase of the plant transfer function in degrees.
    """
    omega: ndarray
    margin: ndarray
    phase: ndarray


@dataclass
class ControllerTransferContext:
    """Input parameters for computing the controller frequency response.

    This context contains PID controller parameters used to evaluate
    the controller transfer function C(s) in the frequency domain.

    Attributes:
        kp: Proportional gain.
        ti: Integral time constant.
        td: Derivative time constant.
        tf: Derivative filter time constant.
    """
    kp: float
    ti: float
    td: float
    tf: float


@dataclass
class ClosedLoopFrequencyResponseResult:
    """Frequency-domain response of a closed-loop system.

    This dataclass stores the computed frequency-domain results for a
    plant-controller system, including the controller, open-loop,
    sensitivity, and complementary sensitivity responses.

    Attributes:
        omega: Frequency vector (rad/s) at which the responses are evaluated.
        margin_C: Magnitude of the controller transfer function C(s) in dB.
        phase_C: Phase of the controller transfer function C(s) in degrees.
        margin_L: Magnitude of the open-loop transfer function L(s) = C(s)G(s) in dB.
        phase_L: Phase of the open-loop transfer function L(s) in degrees.
        margin_T: Magnitude of the complementary sensitivity function T(s) = L/(1+L) in dB.
        phase_T: Phase of the complementary sensitivity function T(s) in degrees.
        margin_S: Magnitude of the sensitivity function S(s) = 1/(1+L) in dB.
        phase_S: Phase of the sensitivity function S(s) in degrees.
    """
    omega: ndarray
    margin_C: ndarray
    phase_C: ndarray
    margin_L: ndarray
    phase_L: ndarray
    margin_T: ndarray
    phase_T: ndarray
    margin_S: ndarray
    phase_S: ndarray
