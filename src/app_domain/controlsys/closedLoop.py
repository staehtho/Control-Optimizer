# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Module:        closedLoop.py
# Description:   Provides the abstract ClosedLoop base class used to represent and simulate
#                closed-loop systems in the PID Optimizer. Includes transfer function
#                computation, disturbance responses, and step simulation utilities. Concrete
#                controllers must implement the controller() and system_response() methods.
#
# Authors:       Florin Büchi, Thomas Stähli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zürcher Hochschule für angewandte Wissenschaften (or internal use only)
# ──────────────────────────────────────────────────────────────────────────────


from abc import ABC, abstractmethod
from typing import Callable

import numpy as np

from .enums import AntiWindup
from .plant import Plant


class ClosedLoop(ABC):
    def __init__(
            self,
            plant: Plant,
            control_constraint: list[float] = None,
            anti_windup_method: AntiWindup = AntiWindup.CLAMPING
    ):
        """
        Initializes a closed-loop control system.

        Args:
            plant (Plant):
                The plant or process model that the controller interacts with.
            control_constraint (list[float], optional):
                A two-element list defining the minimum and maximum allowable
                control signal (e.g., actuator saturation limits). If not
                provided, defaults to [-5.0, 5.0].
            anti_windup_method (AntiWindup, optional):
                The anti-windup strategy used to handle saturation effects.
                Defaults to ``AntiWindup.CLAMPING``.

        Attributes:
            plant (Plant):
                Internal reference to the plant model.
            control_constraint (list[float]):
                Saturation limits applied to the control output.
            anti_windup_method (AntiWindup):
                Selected anti-windup technique for the controller.
        """
        self._plant = plant
        self._control_constraint = control_constraint or [-5.0, 5.0]
        self._anti_windup_method = anti_windup_method

    def __format__(self, format_spec: str) -> str:
        """
        Format the closed-loop system as a MATLAB-style transfer function string.

        This produces the symbolic closed-loop transfer function:
            G_cl(s) = (C(s) * G(s)) / (1 + C(s) * G(s))

        The controller and system are formatted using their own __format__ methods:
            - Controller:  f"{self:controller}"
            - Plant:       f"{self._plant:system}"

        Args:
            format_spec (str): Format type.
                - "cl": MATLAB-style closed-loop expression.

        Returns:
            str: MATLAB-formatted closed-loop transfer function string.

        Raises:
            NotImplementedError: If the format_spec is not supported.
        """
        # Formatstring bereinigen
        format_spec = format_spec.strip().lower()

        if format_spec == "cl":
            controller_str = format(self, "controller")
            system_str = format(self._plant, "system")

            num_str = f"{controller_str} * {system_str}"
            den_str = f"1 + {controller_str} * {system_str}"
            return f"({num_str}) / ({den_str})"
        else:
            raise NotImplementedError(f"Unsupported format specifier: '{format_spec}'")

    @property
    def plant(self) -> Plant:
        return self._plant

    @property
    def control_constraint(self) -> list[float]:
        return self._control_constraint

    @property
    def anti_windup_method(self) -> AntiWindup:
        return self._anti_windup_method

    @abstractmethod
    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """Compute the controller transfer function in the Laplace domain.

        This method must be implemented by all concrete closed-loop controller
        subclasses. It returns the complex-valued controller transfer function
        evaluated at the given Laplace frequency ``s``. Implementations typically
        include proportional, integral, and derivative components, as well as
        derivative filtering.

        Args:
            s (complex | np.ndarray):
                Laplace variable at which the transfer function is evaluated.
                May be a scalar or a NumPy array for vectorized frequency-domain
                evaluation.

        Returns:
            complex | np.ndarray:
                The controller transfer function ``C(s)`` evaluated at ``s``.

        Raises:
            NotImplementedError:
                If a subclass does not implement this method.
        """
        pass

    def closed_loop(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """Compute the closed-loop transfer function.

        Returns the standard unity-feedback closed-loop transfer function

            G_cl(s) = C(s) * G(s) / (1 + C(s) * G(s))

        where ``C(s)`` is the controller transfer function and ``G(s)`` is the
        plant transfer function. The computation supports scalar and vectorized
        Laplace-domain inputs.

        Args:
            s (complex | np.ndarray):
                Laplace variable. Can be a single complex value or a NumPy array
                for frequency-sweep evaluations.

        Returns:
            complex | np.ndarray:
                Closed-loop transfer function ``G_cl(s)`` evaluated at ``s``.
        """
        C = self.controller(s)
        G = self._plant.system(s)
        return (C * G) / (1 + C * G)

    def closed_loop_l(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """Compute the closed-loop transfer function for an input disturbance (l).

        Models the disturbance-to-output transfer path where the disturbance acts
        at the plant input. The resulting transfer function is

            G_l(s) = G(s) / (1 + C(s) * G(s))

        This corresponds to how plant-input disturbances propagate through a
        unity-feedback control loop.

        Args:
            s (complex | np.ndarray):
                Laplace variable. Can be a complex scalar or a NumPy array for
                vectorized frequency-domain evaluation.

        Returns:
            complex | np.ndarray:
                Closed-loop disturbance transfer function ``G_l(s)``.
        """
        C = self.controller(s)
        G = self._plant.system(s)
        return G / (1 + C * G)

    def closed_loop_n(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """Compute the closed-loop transfer function for a measurement disturbance (n).

        Models how disturbances added at the measurement/output propagate to the
        controlled output. The resulting transfer function is

            G_n(s) = 1 / (1 + C(s) * G(s))

        This corresponds to the sensitivity function of a unity-feedback control
        loop and captures how well the controller rejects measurement noise.

        Args:
            s (complex | np.ndarray):
                Laplace variable. Can be a complex scalar or a NumPy array for
                vectorized frequency-domain evaluation.

        Returns:
            complex | np.ndarray:
                Closed-loop transfer function ``G_n(s)`` for measurement disturbances.
        """
        C = self.controller(s)
        G = self._plant.system(s)
        return 1 / (1 + C * G)

    def step_response(
            self,
            t0: float = 0,
            t1: float = 10,
            dt: float = 1e-4
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute the step response of the system.

        This method generates a unit step input signal and computes the corresponding
        system response over a specified time interval using the defined numerical
        integration method.

        Args:
            t0 (float, optional): Start time of the simulation. Defaults to 0.
            t1 (float, optional): End time of the simulation. Defaults to 10.
            dt (float, optional): Time step for the simulation. Defaults to 1e-4.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                A tuple containing:

                - **t_eval** (*np.ndarray*): Array of time points.
                - **y_hist** (*np.ndarray*): Array of system output values corresponding to `t_eval`.

        Notes:
            The step input `r(t)` is defined as a constant signal equal to 1 for all `t >= 0`.

            This method internally calls :meth:`system_response`, which performs the actual
            system simulation given the reference signal.
        """
        r = lambda t: np.ones_like(t)
        return self.system_response(t0, t1, dt, r=r)

    def step_response_l(
            self,
            t0: float = 0,
            t1: float = 10,
            dt: float = 1e-4
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute the step response of the system to a disturbance at the plant input (l).

        This method generates a unit step disturbance applied to the plant input (l)
        and computes the corresponding system response over a specified time interval.

        Args:
            t0 (float, optional): Start time of the simulation. Defaults to 0.
            t1 (float, optional): End time of the simulation. Defaults to 10.
            dt (float, optional): Time step for the simulation. Defaults to 1e-4.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                - **t_eval** (*np.ndarray*): Array of time points.
                - **y_hist** (*np.ndarray*): Array of system output values corresponding to `t_eval`.
        """
        l = lambda t: np.ones_like(t)
        return self.system_response(t0, t1, dt, l=l)

    def step_response_n(
            self,
            t0: float = 0,
            t1: float = 10,
            dt: float = 1e-4
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute the step response of the system to a disturbance at the plant input (n).

        This method generates a unit step disturbance applied to the plant input (n)
        and computes the corresponding system response over a specified time interval.

        Args:
            t0 (float, optional): Start time of the simulation. Defaults to 0.
            t1 (float, optional): End time of the simulation. Defaults to 10.
            dt (float, optional): Time step for the simulation. Defaults to 1e-4.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                - **t_eval** (*np.ndarray*): Array of time points.
                - **y_hist** (*np.ndarray*): Array of system output values corresponding to `t_eval`.
        """
        n = lambda t: np.ones_like(t)
        return self.system_response(t0, t1, dt, n=n)

    @abstractmethod
    def system_response(
            self,
            t0: float,
            t1: float,
            dt: float,
            r: Callable[[np.ndarray], np.ndarray] | None = None,
            l: Callable[[np.ndarray], np.ndarray] | None = None,
            n: Callable[[np.ndarray], np.ndarray] | None = None,
            x0: np.ndarray | None = None,
            y0: float = 0
    ) -> tuple[np.ndarray, np.ndarray]:
        """Simulate the closed-loop time-domain response of the system.

        Computes the time response of the controlled plant under a specified
        reference trajectory and optional disturbances. Implementations must
        propagate the plant dynamics, controller dynamics, and all internal states
        over the time vector defined by ``t0``, ``t1``, and ``dt``.

        The function must return both the simulated time vector and the corresponding
        output trajectory.

        Args:
            t0 (float):
                Simulation start time in seconds.
            t1 (float):
                Simulation end time in seconds.
            dt (float):
                Simulation time step in seconds.
            r (Callable[[np.ndarray], np.ndarray] | None, optional):
                Reference (setpoint) function. Must accept a NumPy time vector and
                return a trajectory of equal length. If ``None``, a zero reference is used.
            l (Callable[[np.ndarray], np.ndarray] | None, optional):
                Input disturbance function applied at the plant input (Z1). If ``None``,
                a zero disturbance is assumed.
            n (Callable[[np.ndarray], np.ndarray] | None, optional):
                Measurement disturbance function added at the output (Z2). If ``None``,
                a zero disturbance is assumed.
            x0 (np.ndarray | None, optional):
                Initial state vector of the plant. If ``None``, a zero state vector
                must be assumed by the implementation.
            y0 (float, optional):
                Initial value of the measured output. Defaults to ``0``.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                A tuple ``(t, y)`` consisting of:
                - ``t``: Time vector used for simulation.
                - ``y``: Output trajectory of the closed-loop system.

        Raises:
            NotImplementedError:
                Must be raised by subclasses that do not implement this method.
        """
        pass
