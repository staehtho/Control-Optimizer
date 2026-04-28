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


from typing import Callable

import numpy as np

from .closedLoop import ClosedLoop
from .enums import AntiWindup, MySolver, ControllerType, map_enum_to_int
from .plant import Plant


class PIDClosedLoop(ClosedLoop):

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
    def Kp(self) -> float:
        """Proportional gain."""
        return self._kp

    @property
    def Ki(self) -> float:
        """Equivalent integral gain of the ISA controller."""
        return self._ki

    @property
    def Kd(self) -> float:
        """Equivalent derivative gain of the ISA controller."""
        return self._kd

    @property
    def Ti(self) -> float:
        """Integral time constant."""
        return self._ti

    @property
    def Td(self) -> float:
        """Derivative time constant."""
        return self._td

    @property
    def Tf(self) -> float:
        """Derivative filter time constant."""
        return self._tf

    def set_filter(self, Tf):
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
        """Set PID controller parameters in either parallel gain form or ISA time-constant form.

        This method allows parameterization of the PID controller using one of two
        mutually exclusive representations:

        **Parallel gain form**
            - ``Kp``: Proportional gain
            - ``Ki``: Integral gain
            - ``Kd``: Derivative gain

        **ISA time-constant form**
            - ``Kp``: Proportional gain
            - ``Ti``: Integral time constant (``Ti = Kp / Ki``)
            - ``Td``: Derivative time constant (``Td = Kd / Kp``)

        Both representations describe the same ideal/ISA additive PID controller.
        This method does not support product-series PID parameterizations.

        Only one representation may be provided. The method automatically converts
        between both representations and stores the equivalent internal parameters:
        ``Kp``, ``Ki``, ``Kd``, ``Ti``, and ``Td``.

        Args:
            Kp (float, optional):
                Proportional gain. Required for both parameterizations.
            Ki (float, optional):
                Integral gain. Used only when specifying the parallel gain form.
            Kd (float, optional):
                Derivative gain. Used only when specifying the parallel gain form.
            Ti (float, optional):
                Integral time constant. Used only when specifying the ISA time-constant form.
            Td (float, optional):
                Derivative time constant. Used only when specifying the ISA time-constant form.

        Raises:
            ValueError:
                If both parameter forms are provided simultaneously.
            ValueError:
                If neither representation is fully provided.
        """
        # --- Parameter Validation ---
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

    # -------------------- Frequency Domain --------------------

    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """
        Compute the PID controller transfer function with derivative filter in the Laplace domain.

        Args:
            s (complex | np.ndarray): Laplace variable.

        Returns:
            complex | np.ndarray: Complex transfer function value.
        """
        P = 1
        I = 1 / (self._ti * s)
        D = (self._td * s) / (self._tf * s + 1)
        return self._kp * (P + I + D)

    @classmethod
    def frf_batch(cls, X: np.ndarray, s: np.ndarray) -> np.ndarray:
        """
        X[:,0] = Kp
        X[:,1] = Ti
        X[:,2] = Td
        X[:,3] = Tf
        """
        with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
            Kp = X[:, 0][:, None]
            Ti = X[:, 1][:, None]
            Td = X[:, 2][:, None]
            Tf = X[:, 3][:, None]
            s_row = s[None, :]
            return Kp * (1 + 1 / (Ti * s_row) + (Td * s_row) / (Tf * s_row + 1))

    # TODO(2026-03-18): Reactivate and fix __format__ only when symbolic MATLAB export
    # is actually needed. The previous implementation was unused in the codebase and
    # algebraically inconsistent with the implemented ISA PID-T1 controller
    # C(s) = Kp * (1 + 1/(Ti*s) + (Td*s)/(Tf*s + 1)).
    #
    # def __format__(self, format_spec: str) -> str:
    #     """
    #     Format the PID-T1 controller as a MATLAB transfer function string.
    #
    #     Example:
    #         >>> format(pid, "controller")
    #         'tf([Td*Ti, Ti, 1], [Ti*Tf, Ti, 0]) * Kp'
    #
    #     Args:
    #         format_spec (str): Format specifier ('controller' for MATLAB-style).
    #
    #     Returns:
    #         str: Formatted MATLAB transfer function string.
    #     """
    #     format_spec = format_spec.strip().lower()
    #     if format_spec == "controller":
    #         num = f"[{self._ti * self._td} {self._ti} 1]"
    #         den = f"[{self._ti * self._tf} {self._ti} 0]"
    #         return f"tf({num}, {den}) * {self._kp}"
    #     elif format_spec == "tf_num":
    #         return "[1 0];"
    #     elif format_spec == "tf_den":
    #         return f"[{self._tf} 1];"
    #     return super().__format__(format_spec)

    # -------------------- Time Domain --------------------

    def system_response(
            self,
            t0: float,
            t1: float,
            dt: float,
            r: Callable[[np.ndarray], np.ndarray] | None = None,
            l: Callable[[np.ndarray], np.ndarray] | None = None,
            n: Callable[[np.ndarray], np.ndarray] | None = None,
            solver: MySolver = MySolver.RK4,
            x0: np.ndarray | None = None,
            y0: float = 0
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute the system response for a given reference signal.

        This method simulates the closed-loop response of a system with a PID controller
        over a specified time interval. It numerically integrates the system dynamics
        based on the system’s state-space representation (A, B, C, D) and applies the
        selected anti-windup strategy.

        Args:
            t0 (float): Start time of the simulation.
            t1 (float): End time of the simulation.
            dt (float): Time step for numerical integration.
            r (Callable[[np.ndarray], np.ndarray] | None, optional):
                Reference (setpoint) function as a function of time.
                Must accept a NumPy array of time values and return an array of the same shape.
                If None, a zero vector is used. Defaults to None.
            l (Callable[[np.ndarray], np.ndarray] | None, optional):
                Disturbance at the plant input (Z1) as a function of time.
                If None, zero disturbance is assumed. Defaults to None.
            n (Callable[[np.ndarray], np.ndarray] | None, optional):
                Disturbance at the measurement/output (Z2) as a function of time.
                If None, zero disturbance is assumed. Defaults to None.
            solver (Solver, optional):
                Numerical integration solver used by the compiled response routine.
                This value is taken from ``self._plant.solver``.
            x0 (np.ndarray | None, optional): Initial state vector of the system. If None, a zero vector of appropriate
                dimension is used. Defaults to None.
            y0 (float, optional): Initial output value. Defaults to 0.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                A tuple containing:

            - **t_eval** (*np.ndarray*):
              Array of time points over the simulation interval.
            - **u** (*np.ndarray*):
              Control signal history u(t) generated by the PID controller.
            - **y** (*np.ndarray*):
              Measured plant output y(t), including measurement disturbance and
              feedthrough term.

        Raises:
            NotImplementedError:
                If an unsupported anti-windup method is specified.

        Notes:
            - The system dynamics are obtained from the state-space matrices (A, B, C, D).
            - The numerical integration solver is taken from ``self._plant.solver`` and
              forwarded to ``pid_system_response()``.
            - Supported anti-windup methods are:
                - `"conditional"`: Update the integrator only when output is within limits or reduces saturation.
                - `"clamping"`: Clamp the integrator term when the actuator saturates.
                - `"backcalculation"`: Unwind the integrator using actuator saturation feedback scaled by ``ka``.
            - The controller's ``ka`` value is forwarded to ``pid_system_response()``.
            - Internally calls the compiled function `pid_system_response()` for performance.
        """
        from app_domain.pso_objective.time_domain_numba import system_response_closed_loop, CONTROLLER_REGISTRY

        t_eval = np.arange(t0, t1 + dt, dt)

        if r is None:
            r = lambda t: np.zeros_like(t)

        if l is None:
            l = lambda t: np.zeros_like(t)

        if n is None:
            n = lambda t: np.zeros_like(t)

        r_eval = r(t_eval)
        l_eval = l(t_eval)
        n_eval = n(t_eval)

        if x0 is None:
            x0 = np.zeros(self._plant.get_plant_order())

        A, B, C, D = self._plant.get_ABCD()

        A = np.ascontiguousarray(A, dtype=np.float64)
        # SISO → (n x 1)
        B = B.flatten()
        B = np.ascontiguousarray(B, dtype=np.float64)
        # SISO → (1 x n) wird aber in ein (n x 1) umgeschrieben (Performance)
        C = C.flatten()
        C = np.ascontiguousarray(C, dtype=np.float64)
        # SISO → D ist ein skalar
        D = float(D[0, 0])

        u, y = system_response_closed_loop(
            kernel=CONTROLLER_REGISTRY[ControllerType.PID].kernel,
            controller_param=np.array([self._kp, self._ti, self._td, self._tf]),
            t_eval=t_eval,
            dt=dt,
            r_eval=r_eval,
            l_eval=l_eval,
            n_eval=n_eval,
            x=np.array(x0),
            control_constraint=np.array(self._control_constraint, dtype=np.float64),
            anti_windup_method=map_enum_to_int(self._anti_windup_method),
            ka=float(self.ka),
            A=A,
            B=B,
            C=C,
            D=D,
            solver=map_enum_to_int(solver)
        )
        return t_eval, u, y
