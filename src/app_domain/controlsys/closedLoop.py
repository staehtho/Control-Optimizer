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

from .enums import AntiWindup, MySolver, map_enum_to_int, ControllerType
from .plant import Plant


class ClosedLoop(ABC):
    controller_type: ControllerType  # each subclass sets this
    tf_link_index: int = -1
    has_integrator: bool = False


    def __init__(
            self,
            plant: Plant,
            control_constraint: list[float] = None,
            anti_windup_method: AntiWindup = AntiWindup.CLAMPING,
            ka: float = 1.0,
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
            ka (float, optional):
                Back-calculation scaling factor used when the selected anti-windup
                strategy is ``BACKCALCULATION``. Defaults to ``1.0``.

        Attributes:
            plant (Plant):
                Internal reference to the plant model.
            control_constraint (list[float]):
                Saturation limits applied to the control output.
            anti_windup_method (AntiWindup):
                Selected anti-windup technique for the controller.
            ka (float):
                Back-calculation scaling factor stored with the controller.
        """
        self._plant = plant
        self._control_constraint = control_constraint or [-5.0, 5.0]
        self._anti_windup_method = anti_windup_method
        self._ka = float(ka)

    @property
    def plant(self) -> Plant:
        return self._plant

    @property
    def control_constraint(self) -> list[float]:
        return self._control_constraint

    @property
    def anti_windup_method(self) -> AntiWindup:
        return self._anti_windup_method

    @property
    def ka(self) -> float:
        """Back-calculation scaling factor."""
        return self._ka

    @abstractmethod
    def get_controller_params(self) -> list[float]:
        pass

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
                Raised by concrete subclasses if controller evaluation is not implemented.
        """
        pass

    @classmethod
    @abstractmethod
    def frf_batch(
            cls,
            plant_tf: Callable[[np.ndarray | complex], np.ndarray | complex],
            X: np.ndarray,
            s: np.ndarray
    ) -> np.ndarray:
        """
        Vectorized batch open-loop frequency response.

        Computes the open-loop transfer function

            L(s) = C(s) * G(s)

        for a batch of controller parameter sets and a shared plant transfer
        function.

        Args:
            plant_tf:
                Callable evaluating the plant transfer function G(s) for scalar
                or vector s.
            X:
                Parameter matrix of shape (P, n_params), where each row contains
                one controller parameter set.
            s:
                Frequency vector of shape (N,) representing the Laplace variable
                s = jω.

        Returns:
            np.ndarray:
                Open-loop frequency response matrix L(jω) of shape (P, N),
                where each row corresponds to one parameter set.
        """
        pass

    def open_loop(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """
        Compute the open‑loop transfer function.

            L(s) = C(s) · G(s)

        where ``C(s)`` is the controller transfer function and ``G(s)`` is the
        plant transfer function. Supports scalar and vectorized Laplace‑domain
        inputs.

        Args:
            s (complex | np.ndarray):
                Laplace variable. May be a single complex value or a NumPy array
                for frequency‑sweep evaluations.

        Returns:
            complex | np.ndarray:
                Open‑loop transfer function ``L(s)`` evaluated at ``s``.
        """
        C = self.controller(s)
        G = self._plant.system(s)
        return C * G

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
        L = self.open_loop(s)
        return L / (1 + L)

    def sensitivity(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """
        Compute the sensitivity function.

            S(s) = 1 / (1 + L(s))

        where ``L(s)`` is the open‑loop transfer function. Supports scalar and
        vectorized Laplace‑domain inputs.

        Args:
            s (complex | np.ndarray):
                Laplace variable. May be a single complex value or a NumPy array
                for frequency‑sweep evaluations.

        Returns:
            complex | np.ndarray:
                Sensitivity function ``S(s)`` evaluated at ``s``.
        """
        L = self.open_loop(s)
        return 1 / (1 + L)

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
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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

    def system_response(
            self,
            t0: float,
            t1: float,
            dt: float,
            r: Callable[[np.ndarray], np.ndarray] | None = None,
            l: Callable[[np.ndarray], np.ndarray] | None = None,
            n: Callable[[np.ndarray], np.ndarray] | None = None,
            solver: MySolver = MySolver.RK4,
            x0: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
            Simulate the closed-loop time-domain response of the system.

            This method performs a complete closed-loop simulation using the plant's
            state-space model and the controller kernel associated with the controller
            type of this instance. The controller is evaluated through the Numba-compiled
            kernel stored in ``CONTROLLER_REGISTRY`` and parameterized by the subclass-
            specific ``get_controller_params()`` implementation.

            The simulation propagates:
                - plant dynamics (A, B, C, D)
                - controller action via the selected kernel
                - reference trajectory r(t)
                - input disturbance l(t)
                - measurement disturbance n(t)
                - anti-windup and actuator constraints

            Subclasses do not override this method. They must only define:
                - ``controller_type`` (enum key for CONTROLLER_REGISTRY)
                - ``get_controller_params()`` returning the controller parameter vector

            Args:
                t0 (float):
                    Simulation start time in seconds.
                t1 (float):
                    Simulation end time in seconds.
                dt (float):
                    Simulation time step in seconds.
                r (Callable[[np.ndarray], np.ndarray] | None, optional):
                    Reference (setpoint) function. If ``None``, a zero reference is used.
                l (Callable[[np.ndarray], np.ndarray] | None, optional):
                    Input disturbance function applied at the plant input. If ``None``,
                    a zero disturbance is used.
                n (Callable[[np.ndarray], np.ndarray] | None, optional):
                    Measurement disturbance added to the plant output. If ``None``,
                    a zero disturbance is used.
                solver (MySolver, optional):
                    Numerical integration method for the plant dynamics.
                x0 (np.ndarray | None, optional):
                    Initial plant state vector. If ``None``, a zero vector is used.

            Returns:
                tuple[np.ndarray, np.ndarray, np.ndarray]:
                    ``(t, u, y)`` where:
                        - ``t`` is the time vector
                        - ``u`` is the control signal trajectory
                        - ``y`` is the plant output trajectory

            Notes:
                This method is controller-agnostic. All controller-specific behavior
                (parameter vector, kernel selection) is delegated to the subclass and
                the controller registry.
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

        A, B, C, D = self._plant.get_state_space_model()

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
            step_fn=CONTROLLER_REGISTRY[self.controller_type].step_fn,
            controller_param=np.array(self.get_controller_params()),
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
