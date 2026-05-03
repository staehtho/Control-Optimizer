# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Module:        PIDClosedLoop.py
# Description:   Implements the PIDClosedLoop class, providing a closed-loop control system
#                based on an ideal/ISA PID controller parameterized either in parallel gain form
#                or in ISA time-constant form. Supports filtered derivative action, output
#                constraints, anti-windup strategies, frequency-domain evaluation, and time-domain
#                simulation via the plant model and compiled response function.
#
# Authors:       Florin Büchi, Thomas Stähli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zürcher Hochschule für angewandte Wissenschaften (or internal use only)
# ──────────────────────────────────────────────────────────────────────────────

import numpy as np

from .closedLoop import ClosedLoop
from .enums import AntiWindup, ControllerType
from .plant import Plant


class PIDClosedLoop(ClosedLoop):
    controller_type = ControllerType.PID

    def __init__(self,
                 plant: Plant,
                 *,
                 # Parallel gain form
                 Kp: float = None,
                 Ki: float = None,
                 Kd: float = None,
                 # ISA time-constant form
                 Ti: float = None,
                 Td: float = None,
                 # Filter
                 Tf: float = 0.01,
                 control_constraint: list[float] = None,
                 anti_windup_method: AntiWindup = AntiWindup.CLAMPING,
                 ka: float = 1.0,
                 ) -> None:

        """
        Closed-loop control system using an ideal/ISA PID controller.

        The controller can be parameterized using either **parallel gain form**
        or **ISA time-constant form**:

        Parallel gain form:
            - Kp: Proportional gain
            - Ki: Integral gain
            - Kd: Derivative gain

        ISA time-constant form:
            - Kp: Proportional gain
            - Ti: Integral time constant
            - Td: Derivative time constant

        Only one parameterization method should be provided during initialization.
        If one form is provided, the parameters of the other form are computed
        automatically.

        The derivative part of the PID controller is filtered using a first-order
        (PT1) filter with time constant `Tf`.

        Implemented transfer function (ideal/ISA form):
            Gc(s) = Kp * (1 + 1/(Ti * s) + (Td * s) / (Tf * s + 1))

        In this project, "time-constant form" refers to the ISA/ideal additive
        PID parameterization above, not to a product-series PID structure.

        Args:
            plant (Plant): The plant being controlled.

            Kp (float, optional): Proportional gain (parallel gain form).
            Ki (float, optional): Integral gain (parallel gain form).
            Kd (float, optional): Derivative gain (parallel gain form).

            Ti (float, optional): Integral time constant (ISA time-constant form).
            Td (float, optional): Derivative time constant (ISA time-constant form).

            Tf (float, optional): Time constant of the derivative PT1 filter.
                Defaults to 0.01.

            control_constraint (list[float], optional):
                A two-element list defining the minimum and maximum allowable
                control signal (e.g., actuator saturation limits). If not
                provided, defaults to [-5.0, 5.0].
            anti_windup_method (AntiWindup, optional):
                The anti-windup strategy used to handle saturation effects.
                Defaults to ``AntiWindup.CLAMPING``.
            ka (float, optional):
                Scaling factor for the back-calculation anti-windup feedback.
                Defaults to ``1.0``.

        Raises:
            ValueError: If both parameterization methods (parallel gain and ISA
                time-constant form) are provided or if neither is provided.
        """

        super().__init__(plant, control_constraint, anti_windup_method, ka)

        self._kp: float = 0
        self._ki: float = 0
        self._kd: float = 0

        self._ti: float = 0
        self._td: float = 0

        self.set_pid_param(Kp=Kp, Ki=Ki, Kd=Kd, Ti=Ti, Td=Td)

        # filter time constant
        self._tf = Tf

    # -------------------- Properties --------------------

    @property
    def Td(self) -> float:
        """Derivative time constant."""
        # TODO: cleanup: to remove
        return self._td

    @property
    def Tf(self) -> float:
        """Derivative filter time constant."""
        # TODO: cleanup: to remove
        return self._tf

    def set_filter(self, Tf):
        # TODO: cleanup: to remove
        self._tf = Tf

    def set_pid_param(self,
                      *,
                      # Parallel gain form
                      Kp: float = None,
                      Ki: float = None,
                      Kd: float = None,
                      # ISA time-constant form
                      Ti: float = None,
                      Td: float = None):
        # --- Parameter Validation ---
        # TODO: cleanup: to remove
        if all(v is None for v in (Kp, Ki, Kd, Ti, Td)):
            Kp = 1.0
            Ti = 1.0
            Td = 1.0

        gain_form = all(v is not None for v in (Kp, Ki, Kd))
        time_form = all(v is not None for v in (Kp, Ti, Td))

        if gain_form and time_form:
            raise ValueError("Use either (Kp, Ki, Kd) or (Kp, Ti, Td), not both.")
        if not (gain_form or time_form):
            raise ValueError("You must provide either the parallel gain form or the ISA time-constant form.")

        # --- Assign Parameters and Convert if Needed ---
        self._kp = Kp

        if gain_form:
            # Gain → Time conversion
            self._ki = Ki
            self._kd = Kd
            self._ti = Kp / Ki
            self._td = Kd / Kp
        else:
            # Time → Gain conversion
            self._ti = Ti
            self._td = Td
            self._ki = Kp / Ti
            self._kd = Kp * Td

    def get_controller_params(self) -> list[float]:
        return [self._kp, self._ti, self._td, self._tf]

    # -------------------- Frequency Domain --------------------
    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        X = np.array([[self._kp, self._ti, self._td, self._tf]])
        return self.frf_batch(X, np.atleast_1d(s))[0]

    @classmethod
    def transfer_function(cls, s: complex | np.ndarray, **params) -> complex | np.ndarray:
        X = np.array([[params["Kp"], params["Ti"], params["Td"], params["Tf"]]])
        return cls.frf_batch(X, np.atleast_1d(s))[0]

    @classmethod
    def frf_batch(cls, X: np.ndarray, s: np.ndarray) -> np.ndarray:
        """Vectorized frequency response (core implementation)."""
        Kp = X[:, 0][:, None]
        Ti = X[:, 1][:, None]
        Td = X[:, 2][:, None]
        Tf = X[:, 3][:, None]
        s_row = s[None, :]
        return Kp * (1 + 1 / (Ti * s_row) + (Td * s_row) / (Tf * s_row + 1))
