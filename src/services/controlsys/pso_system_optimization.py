# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Module:        pso_system_optimization.py
# Description:   Provides Numba-accelerated simulation routines and performance index evaluation
#                for PSO-based PID optimization. Includes PID update logic, ODE solvers,
#                closed-loop and open-loop response functions, and a vectorized PSO objective
#                function for evaluating multiple PID parameter sets in parallel.
#
# Authors:       Florin Büchi, Thomas Stähli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zürcher Hochschule für angewandte Wissenschaften (or internal use only)
# ──────────────────────────────────────────────────────────────────────────────


import time
from typing import Callable

import numpy as np
from numba import njit, prange, types, float64, int64

from .PIDClosedLoop import PIDClosedLoop
from .closedLoop import ClosedLoop
from .enums import *


class PsoFunc:
    """
    Wrapper for Particle Swarm Optimization (PSO) of a PID controller.

    Prepares a PID controller for optimization using PSO by exposing a unified
    call interface that returns a chosen performance index (e.g. ITAE) for a
    batch of PID parameter sets. Internally this class evaluates the closed-loop
    response of a SISO system under PID control and supports disturbances at the
    plant input (Z1) and at the measurement/output (Z2).

    The class pre-compiles Numba-jitted helper functions for faster repeated
    evaluations.
    """
    def __init__(self, controller: ClosedLoop, t0: float, t1: float, dt: float,
                 r: Callable[[np.ndarray], np.ndarray] | None = None,
                 l: Callable[[np.ndarray], np.ndarray] | None = None,
                 n: Callable[[np.ndarray], np.ndarray] | None = None,
                 solver: MySolver = MySolver.RK4,
                 performance_index: PerformanceIndex = PerformanceIndex.ITAE,
                 swarm_size: int = 40,
                 pre_compiling: bool = True) -> None:
        """
        Initialize a PsoFunc instance.

        Args:
            controller: PID controller instance to be optimized.
            t0: Simulation start time.
            t1: Simulation end time.
            dt: Simulation time step.
            r: Reference (setpoint) function defining the desired output over time.
                If None, a zero vector is used.
            l: Disturbance function at the plant input (Z1). If None, zero disturbance is assumed.
            n: Disturbance function at the measurement/output (Z2). If None, zero disturbance is assumed.
            solver: Solver enum to choose the ODE integrator (default: RK4).
            performance_index: Performance index enum (IAE/ISE/ITAE/ITSE).
            swarm_size: Number of particles in the swarm for PSO. Defaults to 40.
            pre_compiling: If True, run one warm-up call to pre-compile Numba functions.

        Raises:
            NotImplementedError: If the provided controller is not a supported type.
        """

        self.controller = controller

        self.t0 = t0
        self.t1 = t1
        self.dt = dt
        self.t_eval = np.arange(t0, t1 + dt, dt)

        self._pre_compiling = pre_compiling

        if r is None:
            r = lambda t: np.zeros_like(t)

        if l is None:
            l = lambda t: np.zeros_like(t)

        if n is None:
            n = lambda t: np.zeros_like(t)

        self.r_eval = r(self.t_eval)
        self.l_eval = l(self.t_eval)
        self.n_eval = n(self.t_eval)

        # Extract state-space matrices and ensure they are contiguous for Numba
        A, B, C, D = self.controller.plant.get_ABCD()
        self.A = A
        self.A = np.ascontiguousarray(A, dtype=np.float64)
        # SISO → (n x 1)
        self.B = B.flatten()
        self.B = np.ascontiguousarray(self.B, dtype=np.float64)
        # SISO → (1 x n) wird aber in ein (n x 1) umgeschrieben (Performance)
        self.C = C.flatten()
        self.C = np.ascontiguousarray(self.C, dtype=np.float64)
        # SISO → D ist ein skalar
        self.D = float(D[0, 0])

        self.plant_order = self.controller.plant.get_plant_order()

        self.controller_param: dict[str, str | float | np.ndarray]

        self.performance_index = map_enum_to_int(performance_index)
        self.control_constraint = np.array(self.controller.control_constraint, dtype=np.float64)
        self.anti_windup_method = map_enum_to_int(self.controller.anti_windup_method)

        self.solver = map_enum_to_int(solver)

        self.swarm_size = swarm_size

        # Pre-compile Numba functions
        if self._pre_compiling:
            start = time.time()
            X = np.array([[10, 9.6, 0.3] for _ in range(swarm_size)], dtype=np.float64)
            self.__call__(X)
            end = time.time()
            print(f"Pre-compiling: {end - start:0.6f} sec", flush=True)
            time.sleep(0.05)

            self._pre_compiling = False

    def __call__(self, X: np.ndarray) -> np.ndarray:
        """
        Evaluate the selected performance index for a batch of PID parameter sets.

        Args:
            X: PID parameter matrix of shape (swarm_size, 3). Each row contains [Kp, Ti, Td].

        Returns:
            A 1-D array with the performance index value for each particle.
        """
        X = np.array(X, dtype=np.float64)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        if isinstance(self.controller, PIDClosedLoop):
            itae_val = _pid_pso_func(X, self.t_eval, self.dt, self.r_eval, self.l_eval, self.n_eval, self.A, self.B,
                                     self.C, self.D, self.plant_order, self.controller.Tf,
                                     self.control_constraint, self.anti_windup_method,
                                     self.solver, self.performance_index, self.swarm_size)

        else:
            raise NotImplementedError(f"Unsupported controller type: '{type(self.controller)}'")

        return itae_val


# =============================================================================
# Helper Functions
# =============================================================================
@njit(float64[:](float64[:, :], float64[:]), cache=True, inline="always")
def _matvec_auto(A: np.ndarray, x: np.ndarray) -> np.ndarray:
    """
    Perform matrix-vector multiplication manually for Numba.

    Args:
        A: Square matrix.
        x: Vector.

    Returns:
        Result of A @ x as a 1-D numpy array.
    """
    n = A.shape[0]
    y = np.zeros(n)

    for i in range(n):
        acc = 0.0
        for j in range(n):
            acc += A[i][j] * x[j]
        y[i] = acc

    return y


@njit(float64(float64[:], float64[:]), cache=True, inline="always")
def dot1D(x: np.ndarray, y: np.ndarray) -> float:
    """
    Compute dot product of two 1-D vectors manually for Numba.

    Args:
        x: Vector x.
        y: Vector y.

    Returns:
        The scalar dot product x.T @ y.
    """
    acc = 0.0
    for i in range(x.shape[0]):
        acc += x[i] * y[i]
    return acc


# =============================================================================
# PID Update
# =============================================================================
@njit(
    types.UniTuple(float64, 3)(
        float64, float64, float64, float64, float64, float64, float64, float64, float64, float64, float64, int64
    ),
    cache=True, inline="always"
)
def pid_update(e: float, e_prev: float, d_filtered_prev: float, integral_prev: float,
               Kp: float, Ti: float, Td: float, Tf: float, dt: float, u_min: float, u_max: float,
               anti_windup_method: int) -> tuple[float, float, float]:
    """
    Perform a single PID controller update including anti-windup.

    The function computes proportional, integral and filtered derivative terms,
    applies the selected anti-windup strategy and returns the saturated control
    signal together with the updated integral and filtered derivative states.

    Args:
        e: Current error.
        e_prev: Previous error.
        d_filtered_prev: Previous filtered derivative term.
        integral_prev: Previous integral state (accumulated error integral).
        Kp: Proportional gain.
        Ti: Integral time constant.
        Td: Derivative time constant.
        Tf: Derivative filter time constant.
        dt: Simulation time step.
        u_min: Lower control limit.
        u_max: Upper control limit.
        anti_windup_method: Anti-windup strategy (0=Conditional, 1=Clamping).

    Returns:
        A tuple with three floats: (u, integral, d_filtered)
        - u_updated: The saturated control output.
        - integral_updated: Updated integral state.
        - d_filtered_updated: Updated filtered derivative state.
    """

    # --------------------------------------------------
    # 1) Proportional block
    # --------------------------------------------------
    P_term = Kp * e

    # --------------------------------------------------
    # 2) Integration block
    # --------------------------------------------------
    if Ti > 0.0:
        integral_candidate = integral_prev + e * dt
    else:
        integral_candidate = integral_prev

    # previous integrator (scaled for parallelform)
    I_term_previous = Kp * (1.0 / Ti) * integral_prev if Ti > 0 else 0.0

    # candidate integrator (scaled for parallelform)
    I_term_candidate = Kp * (1.0 / Ti) * integral_candidate if Ti > 0 else 0.0

    # --------------------------------------------------
    # 3) Derivative block (filtered)
    # --------------------------------------------------
    if Td > 0.0:
        alpha = Tf / (Tf + dt)
        d_filtered_updated = alpha * d_filtered_prev + (1.0 - alpha) * ((e - e_prev) / dt)
    else:
        d_filtered_updated = 0.0

    # D-Term scaled for parallelform
    D_term = Kp * Td * d_filtered_updated

    # --------------------------------------------------
    # 4) PID-Build
    # --------------------------------------------------
    # unsaturated control output with previous I-term
    u_unsat_previous = P_term + I_term_previous + D_term

    # unsaturated control output with candidate I-term
    u_unsat_candidate = P_term + I_term_candidate + D_term

    # --------------------------------------------------
    # 5) Anti-windup
    # --------------------------------------------------
    if anti_windup_method == AntiWindupInt.CONDITIONAL:

        # Allow integration only if it will not cause saturation on control output
        if (u_min < u_unsat_candidate < u_max) or \
                (u_unsat_candidate >= u_max and e < 0.0) or \
                (u_unsat_candidate <= u_min and e > 0.0):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_previous

    elif anti_windup_method == AntiWindupInt.CLAMPING:

        # Allow integration only if it will not cause saturation inside integration
        if (u_min < I_term_candidate < u_max) or \
                (I_term_candidate >= u_max and e < 0.0) or \
                (I_term_candidate <= u_min and e > 0.0):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_previous

    else:
        u_unsat_updated = 0.0         # safety fallback
        integral_updated = 0.0        # safety fallback

    # --------------------------------------------------
    # 6) Output Saturation
    # --------------------------------------------------
    u_updated = min(max(u_unsat_updated, u_min), u_max)

    # --------------------------------------------------
    # 7) Output
    # --------------------------------------------------
    return u_updated, integral_updated, d_filtered_updated


# =============================================================================
# ODE Solver
# =============================================================================
@njit(float64[:](float64[:, :], float64[:], float64[:], float64, float64), cache=True, inline="always")
def rk4(A: np.ndarray, B: np.ndarray, x: np.ndarray, u: float, dt: float) -> np.ndarray:
    """
    Perform a single Runge–Kutta 4th order (RK4) integration step.

    Args:
        A: Plant matrix.
        B: Input matrix.
        x: Current state vector.
        u: Control input (scalar).
        dt: Integration time step.

    Returns:
        The updated state vector after one RK4 step.
    """
    Bu = B * u
    k1 = _matvec_auto(A, x) + Bu
    k2 = _matvec_auto(A, x + 0.5 * dt * k1) + Bu
    k3 = _matvec_auto(A, x + 0.5 * dt * k2) + Bu
    k4 = _matvec_auto(A, x + dt * k3) + Bu
    x += (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    return x


# =============================================================================
# Performance index
# =============================================================================
@njit(float64(float64[:], float64[:], float64[:]), cache=True, inline="always")
def iae(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    """
    Compute the Integral of Absolute Error (IAE).

    IAE = integral |r(t) - y(t)| dt over the provided time vector.

    Args:
        t: Time vector [s].
        y: Plant output trajectory.
        r: Reference trajectory.

    Returns:
        The scalar IAE value.
    """
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += abs(r[i] - y[i]) * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), cache=True, inline="always")
def ise(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    """
    Compute the Integral of Squared Error (ISE).

    ISE = integral (r(t) - y(t))^2 dt over the provided time vector.

    Args:
        t: Time vector [s].
        y: Plant output trajectory.
        r: Reference trajectory.

    Returns:
        The scalar ISE value.
    """
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += (r[i] - y[i])**2 * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), cache=True, inline="always")
def itae(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    """
    Compute the Integral of Time-weighted Absolute Error (ITAE).

    ITAE = integral t * |r(t) - y(t)| dt over the provided time vector.

    Args:
        t: Time vector [s].
        y: Plant output trajectory.
        r: Reference trajectory.

    Returns:
        The scalar ITAE value.
    """
    # berechnet delta t, beginnend mit t[0] - t[0]
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += t[i] * abs(r[i] - y[i]) * dt

    return val


@njit(float64(float64[:], float64[:], float64[:]), cache=True, inline="always")
def itse(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    """
    Compute the Integral of Time-weighted Squared Error (ITSE).

    ITSE = integral t * (r(t) - y(t))^2 dt over the provided time vector.

    Args:
        t: Time vector [s].
        y: Plant output trajectory.
        r: Reference trajectory.

    Returns:
        The scalar ITSE value.
    """
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += t[i] * (r[i] - y[i])**2 * dt
    return val


# =============================================================================
# Plant Response
# =============================================================================
@njit(float64[:](
    float64[:], float64, float64[:], float64[:],
    float64[:, :], float64[:], float64[:], float64, int64
),
    cache=True, inline="always"
)
def system_response(t_eval: np.ndarray, dt: float, u_eval: np.ndarray,
                    x: np.ndarray, A: np.ndarray, B: np.ndarray,
                    C: np.ndarray, D: float, solver: int) -> np.ndarray:
    """
    Simulate the open-loop (uncontrolled) response of a SISO system.

    The system is assumed linear time-invariant in state-space form:

        dx/dt = A * x + B * u
        y = C * x + D * u

    Args:
        t_eval: Time vector for simulation.
        dt: Integration time step.
        u_eval: Input trajectory (e.g., step input).
        x: Initial state vector.
        A: Plant matrix.
        B: Input matrix.
        C: Output matrix.
        D: Feedthrough term (scalar).
        solver: Solver enum value.

    Returns:
        The plant output trajectory y(t) as a 1-D numpy array.
    """
    n_steps = len(t_eval)
    y_hist = np.zeros(n_steps)

    for i in range(n_steps):
        u = float(u_eval[i])

        # Zustand aktualisieren (numerische Integration)
        match solver:
            case MySolverInt.RK4:
                x = rk4(A, B, x, u, dt)

        # Ausgang berechnen
        y = dot1D(C, x)
        y_hist[i] = y + D * u

    return y_hist


@njit(float64[:](
    float64, float64, float64, float64,
    float64[:], float64,
    float64[:], float64[:], float64[:], float64[:], float64[:],
    int64, float64[:, :], float64[:], float64[:], float64, int64
), cache=True, inline="always")
def pid_system_response(Kp: float, Ti: float, Td: float, Tf: float,
                        t_eval: np.ndarray, dt: float,
                        r_eval: np.ndarray, l_eval: np.ndarray, n_eval: np.ndarray,
                        x: np.ndarray, control_constraint: np.ndarray,
                        anti_windup_method: int,
                        A: np.ndarray, B: np.ndarray, C: np.ndarray, D: float, solver: int) -> np.ndarray:
    """
    Simulate a SISO system under PID control with reference and two disturbances (Z1, Z2).

    The function advances the plant state and controller states over t_eval and
    returns the measured output (including measurement disturbance and feedthrough).

    Args:
        Kp: Proportional gain.
        Ti: Integral time constant.
        Td: Derivative time constant.
        Tf: Derivative filter time constant.
        t_eval: Time vector.
        dt: Simulation time step.
        r_eval: Reference trajectory.
        l_eval: Disturbance at plant input (Z1).
        n_eval: Disturbance at measurement/output (Z2).
        x: Initial state vector.
        control_constraint: Control limits [u_min, u_max].
        anti_windup_method: Anti-windup strategy (0=Conditional, 1=Clamping).
        A: Plant matrix.
        B: Input matrix.
        C: Output matrix.
        D: Feedthrough scalar.
        solver: Solver enum value.

    Returns:
        The output trajectory y(t) (measured output including measurement disturbance).
    """
    e_prev = 0.0
    filtered_prev = 0.0
    integral = 0.0

    u_min = float(control_constraint[0])
    u_max = float(control_constraint[1])

    n_steps = len(t_eval)
    y_hist = np.zeros(n_steps)
    y = dot1D(C, x)

    for i in range(n_steps):
        r = float(r_eval[i])
        l = float(l_eval[i])  # Störung am Eingang (Z1)
        n = float(n_eval[i])  # Störung im Messpfad (Z2)

        # Reglerfehler (PID sieht die Messstörung)
        e = r - (y + n)

        # PID-Regler
        u, integral, filtered_prev = pid_update(
            e, e_prev, filtered_prev, integral, Kp, Ti, Td, Tf,
            dt, u_min, u_max, anti_windup_method
        )

        # Systemzustand aktualisieren
        if solver == MySolverInt.RK4:
            x = rk4(A, B, x, u + l, dt)

        # Ausgang berechnen (reales y ohne Messrauschen)
        y = dot1D(C, x)

        # Historie: nur das reale Ausgangssignal plus Feedthrough
        y_hist[i] = y + n + D * (u + l)

        e_prev = e

    return y_hist


# =============================================================================
# PSO Function
# =============================================================================
@njit(parallel=True, cache=True)
def _pid_pso_func(X: np.ndarray, t_eval: np.ndarray, dt: float, r_eval: np.ndarray, l_eval: np.ndarray,
                  n_eval: np.ndarray, A: np.ndarray, B: np.ndarray, C: np.ndarray, D: float,
                  system_order: int, Tf: float, control_constraint: np.ndarray, anti_windup_method: int,
                  solver: int, performance_index: int, swarm_size: int) -> np.ndarray:
    """
    Compute performance index values for multiple PID parameter sets in parallel.

    This function evaluates the closed-loop response for each particle (row in X)
    and computes the requested performance index (IAE/ISE/ITAE/ITSE).

    Args:
        X: PID parameters (Kp, Ti, Td) for each particle, shape (swarm_size, 3).
        t_eval: Time vector.
        dt: Simulation time step.
        r_eval: Reference trajectory.
        l_eval: Disturbance at plant input.
        n_eval: Disturbance at measurement path.
        A: Plant matrix.
        B: Input matrix.
        C: Output matrix.
        D: Feedthrough scalar.
        system_order: Order of the system.
        Tf: Derivative filter time constant.
        control_constraint: Control limits [u_min, u_max].
        anti_windup_method: Anti-windup strategy (0=Conditional, 1=Clamping).
        solver: Solver enum value.
        performance_index: Performance index enum value.
        swarm_size: Number of particles.

    Returns:
        1-D array with the performance index value for each particle.
    """
    performance_index_val = np.zeros(swarm_size)

    for i in prange(swarm_size):
        # Simulation des PID-regulierten Systems
        Kp = float(X[i, 0])
        Ti = float(X[i, 1])
        Td = float(X[i, 2])

        x = np.zeros(system_order, dtype=np.float64)  # Anfangszustand

        y = pid_system_response(Kp, Ti, Td, Tf, t_eval, dt, r_eval, l_eval, n_eval, x, control_constraint,
                                anti_windup_method, A, B, C, D, solver)

        # Kosten berechnen
        match performance_index:
            case PerformanceIndexInt.IAE:
                performance_index_val[i] = iae(t_eval, y, r_eval)

            case PerformanceIndexInt.ISE:
                performance_index_val[i] = ise(t_eval, y, r_eval)

            case PerformanceIndexInt.ITAE:
                performance_index_val[i] = itae(t_eval, y, r_eval)

            case PerformanceIndexInt.ITSE:
                performance_index_val[i] = itse(t_eval, y, r_eval)

    return performance_index_val
