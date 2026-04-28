# ------------------------------------------------------------------------------
# Project:       PID Optimizer
# Module:        pso_system_optimization.py
# Description:   Provides Numba-accelerated simulation routines and performance index evaluation
#                for PSO-based PID optimization. Includes PID update logic, ODE solvers,
#                closed-loop and open-loop response functions, and a vectorized PSO objective
#                function for evaluating multiple PID parameter sets in parallel.
#
# Authors:       Florin Buechi, Thomas Staehli
# Created:       01.12.2025
# Modified:      09.03.2026
# Version:       1.2
#
# License:       ZHAW Zuercher Hochschule fuer angewandte Wissenschaften (or internal use only)
# ------------------------------------------------------------------------------

import numpy as np
from numba import njit, prange, types, float64, int64
from app_domain.controlsys.enums import ControllerType, PerformanceIndexInt, AntiWindupInt, MySolverInt


# =============================================================================
# Helper Functions
# =============================================================================
@njit(float64[:](float64[:, :], float64[:]), inline="always")
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


@njit(float64(float64[:], float64[:]), inline="always")
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
        float64, float64, float64, float64, float64, float64, float64, float64, float64, float64, float64, int64,
        float64
    ),
    inline="always"
)
def pid_update(e: float, e_prev: float, d_filtered_prev: float, integral_prev: float,
               Kp: float, Ti: float, Td: float, Tf: float, dt: float, u_min: float, u_max: float,
               anti_windup_method: int, ka: float) -> tuple[float, float, float]:
    """
    Perform a single PID controller update including anti-windup.

    The function computes proportional, integral and filtered derivative terms,
    applies the selected anti-windup strategy and returns the saturated control
    signal together with the updated integral and filtered derivative states.

    The application-level controller representation remains the ISA
    time-constant form ``(Kp, Ti, Td, Tf)``. Inside this numerical kernel, the
    integral and derivative contributions are evaluated through the equivalent
    local gain terms ``Ki = Kp / Ti`` and ``Kd = Kp * Td`` for efficiency.

    Args:
        e: Current control error.
        e_prev: Previous control error.
        d_filtered_prev: Previous filtered derivative state.
        integral_prev: Previous integral state.
        Kp: Proportional gain.
        Ti: Integral time constant.
        Td: Derivative time constant.
        Tf: Derivative filter time constant.
        dt: Simulation time step.
        u_min: Lower actuator limit.
        u_max: Upper actuator limit.
        anti_windup_method: Selected anti-windup method.
        ka: Scaling factor for the back-calculation feedback path.
    """
    # 1) Proportional
    P_term = Kp * e

    # 2) Integration
    if Ti > 0.0:
        integral_candidate = integral_prev + e * dt
    else:
        integral_candidate = integral_prev

    # Local gain-equivalent evaluation of the ISA controller: Ki = Kp / Ti.
    I_term_previous = Kp * (1.0 / Ti) * integral_prev if Ti > 0 else 0.0
    I_term_candidate = Kp * (1.0 / Ti) * integral_candidate if Ti > 0 else 0.0

    # 3) Derivative (filtered)
    if Td > 0.0:
        alpha = Tf / (Tf + dt)
        d_filtered_updated = alpha * d_filtered_prev + (1.0 - alpha) * ((e - e_prev) / dt)
    else:
        d_filtered_updated = 0.0

    # Local gain-equivalent evaluation of the ISA controller: Kd = Kp * Td.
    D_term = Kp * Td * d_filtered_updated

    # 4) Build u (unsat)
    u_unsat_previous = P_term + I_term_previous + D_term
    u_unsat_candidate = P_term + I_term_candidate + D_term

    # 5) Anti-windup
    if anti_windup_method == AntiWindupInt.CONDITIONAL:
        if (u_min < u_unsat_candidate < u_max) or \
                (u_unsat_candidate >= u_max and e < 0.0) or \
                (u_unsat_candidate <= u_min and e > 0.0):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_previous

    elif anti_windup_method == AntiWindupInt.CLAMPING:
        if (u_min < I_term_candidate < u_max) or \
                (I_term_candidate >= u_max and e < 0.0) or \
                (I_term_candidate <= u_min and e > 0.0):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_previous

    elif anti_windup_method == AntiWindupInt.BACKCALCULATION:
        u_sat_candidate = min(max(u_unsat_candidate, u_min), u_max)

        # The application state integrates the unscaled integral state x_I
        # with I_term = Ki * x_I and Ki = Kp / Ti. A block diagram that feeds
        # the saturation error through the scaling factor ka into the already
        # scaled I-branch therefore maps to ka * (u_sat - u_unsat) / Ki on this state.
        if Ti > 0.0 and Kp != 0.0:
            integral_updated = integral_candidate + dt * ka * (Ti / Kp) * (u_sat_candidate - u_unsat_candidate)
        else:
            integral_updated = integral_candidate

        I_term_updated = Kp * (1.0 / Ti) * integral_updated if Ti > 0.0 else 0.0
        u_unsat_updated = P_term + I_term_updated + D_term

    else:
        u_unsat_updated = 0.0
        integral_updated = 0.0

    # 6) Saturation
    u_updated = min(max(u_unsat_updated, u_min), u_max)

    return u_updated, integral_updated, d_filtered_updated

@njit(inline="always")
def pid_kernel(
        e: float,
        e_prev: float,
        filtered_prev: float,
        integral: float,
        dt: float,
        u_min: float,
        u_max: float,
        controller_param: np.ndarray,
        anti_windup_method: int,
        ka: float
) -> tuple[float, float, float]:
    Kp, Ti, Td, Tf = controller_param
    return pid_update(
        e, e_prev, filtered_prev, integral,
        Kp, Ti, Td, Tf,
        dt, u_min, u_max,
        anti_windup_method, ka
    )



# =============================================================================
# ODE Solver
# =============================================================================
@njit(float64[:](float64[:, :], float64[:], float64[:], float64, float64), inline="always")
def rk4(A: np.ndarray, B: np.ndarray, x: np.ndarray, u: float, dt: float) -> np.ndarray:
    """Perform a single RK4 integration step."""
    Bu = B * u
    k1 = _matvec_auto(A, x) + Bu
    k2 = _matvec_auto(A, x + 0.5 * dt * k1) + Bu
    k3 = _matvec_auto(A, x + 0.5 * dt * k2) + Bu
    k4 = _matvec_auto(A, x + dt * k3) + Bu
    x += (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return x


@njit(inline="always")
def plant_step(
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: float,
        x: np.ndarray,
        u: float,
        l: float,
        n: float,
        dt: float,
        solver: int
) -> tuple[np.ndarray, float, float]:
    """
    One simulation step of the plant:
    - advances the state x
    - computes y (pure plant output)
    - computes y_out (measured output incl. disturbance + feedthrough)
    """
    if solver == MySolverInt.RK4:
        x = rk4(A, B, x, u + l, dt)

    y = dot1D(C, x)
    y_out = y + n + D * (u + l)

    return x, y, y_out


# =============================================================================
# Performance index
# =============================================================================
@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def iae(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += abs(r[i] - y[i]) * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def ise(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += (r[i] - y[i]) ** 2 * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def itae(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += t[i] * abs(r[i] - y[i]) * dt
    return val


@njit(float64(float64[:], float64[:], float64[:]), inline="always")
def itse(t: np.ndarray, y: np.ndarray, r: np.ndarray) -> float:
    val = 0.0
    for i in range(1, t.shape[0]):
        dt = t[i] - t[i - 1]
        val += t[i] * (r[i] - y[i]) ** 2 * dt
    return val


# =============================================================================
# Plant Response
# =============================================================================
@njit(float64[:](
    float64[:], float64, float64[:], float64[:],
    float64[:, :], float64[:], float64[:], float64, int64
),
    inline="always"
)
def system_response(t_eval: np.ndarray, dt: float, u_eval: np.ndarray,
                    x: np.ndarray, A: np.ndarray, B: np.ndarray,
                    C: np.ndarray, D: float, solver: int) -> np.ndarray:
    n_steps = len(t_eval)
    y_hist = np.zeros(n_steps)

    for i in range(n_steps):
        u = float(u_eval[i])

        x, y, y_out = plant_step(A, B, C, D, x, u, 0, 0, dt, solver)

        y = dot1D(C, x)
        y_hist[i] = y + D * u

    return y_hist


# =============================================================================
# System Response
# =============================================================================
@njit(inline="always")
def system_response_closed_loop(
        kernel,
        controller_param: np.ndarray,
        t_eval: np.ndarray,
        dt: float,
        r_eval: np.ndarray,
        l_eval: np.ndarray,
        n_eval: np.ndarray,
        x: np.ndarray,
        control_constraint: np.ndarray,
        anti_windup_method: int,
        ka: float,
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: float,
        solver: int
) -> tuple[np.ndarray, np.ndarray]:
    """
    Simulate a SISO system under PID control with reference and two disturbances (Z1, Z2).

    The function advances the plant state and controller states over `t_eval` and
    returns both the control signal history and the measured output trajectory.

    Args:
        kernel: Simulation kernel.
        controller_param: Parameter from controller
        t_eval: Time vector.
        dt: Simulation time step.
        r_eval: Reference trajectory.
        l_eval: Disturbance at plant input (Z1).
        n_eval: Disturbance at measurement/output (Z2).
        x: Initial state vector.
        control_constraint: Control limits [u_min, u_max].
        anti_windup_method: Anti-windup strategy enum value.
        ka: Scaling factor applied to the back-calculation feedback term.
        A: Plant state matrix.
        B: Input matrix.
        C: Output matrix.
        D: Feedthrough scalar.
        solver: Solver enum value.

    Returns:
        u_hist:
            Control signal history u(t), shape (n_steps,).

        y_hist:
            Measured output history y(t), including measurement disturbance and
            feedthrough term, shape (n_steps,).
    """
    e_prev = 0.0
    filtered_prev = 0.0
    integral = 0.0

    u_min = float(control_constraint[0])
    u_max = float(control_constraint[1])

    n_steps = len(t_eval)
    y_hist = np.zeros(n_steps)
    u_hist = np.zeros(n_steps)

    y = dot1D(C, x)

    for i in range(n_steps):
        r = float(r_eval[i])
        l = float(l_eval[i])
        n = float(n_eval[i])

        e = r - (y + n)

        u, integral, filtered_prev = kernel(
            e,
            e_prev,
            filtered_prev,
            integral,
            dt,
            u_min,
            u_max,
            controller_param,
            anti_windup_method,
            ka
        )

        if np.isnan(u):
            return np.ones_like(t_eval) * np.inf, np.ones_like(t_eval) * np.inf

        x, y, y_out = plant_step(A, B, C, D, x, u, l, n, dt, solver)

        u_hist[i] = u
        y_hist[i] = y_out

        e_prev = e

    return u_hist, y_hist


# =============================================================================
# PSO helper
# =============================================================================
@njit(inline="always")
def simulate_metrics(
        kernel,
        controller_param: np.ndarray,
        t_eval: np.ndarray,
        dt: float,
        r_eval: np.ndarray,
        l_eval: np.ndarray,
        n_eval: np.ndarray,
        x: np.ndarray,
        control_constraint: np.ndarray,
        anti_windup_method: int,
        ka: float,
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: float,
        solver: int,
        performance_index: int,
        use_overshoot_control: int,
        overshoot_step_amplitude_abs: float,
        overshoot_step_start_idx: int,
        overshoot_step_sign: float,
        overshoot_r_final: float,
        calculate_max_du_dt: int,
        du_dt_window_steps: int,
) -> tuple[float, float, float]:
    """Simulate one PID candidate and return time-domain evaluation metrics.

    Overshoot is tracked only from the precomputed step start index onward.
    Anti-windup behavior, including back-calculation scaling via ``ka``,
    is applied in the internal PID update step.

    Returns:
        tuple[float, float, float]:
            ``(performance_index_value, overshoot_pct, max_du_dt)``

        ``max_du_dt`` is computed only when ``calculate_max_du_dt`` is enabled.
        It represents the maximum absolute finite-difference control-rate
        estimate over a sliding window of ``du_dt_window_steps`` samples:
        ``max(|u[k] - u[k-m]| / (m * dt))`` with ``m = du_dt_window_steps``.
    """
    e_prev = 0.0
    filtered_prev = 0.0
    integral = 0.0

    u_min = float(control_constraint[0])
    u_max = float(control_constraint[1])

    y = dot1D(C, x)
    perf = 0.0

    max_overshoot = 0.0
    use_ov = use_overshoot_control != 0
    use_du_dt = calculate_max_du_dt != 0
    max_du_dt = np.nan
    window_steps = du_dt_window_steps
    window_dt = 0.0
    u_hist = np.empty(1, dtype=np.float64)
    if use_du_dt:
        max_du_dt = 0.0
        window_dt = float(window_steps) * dt
        u_hist = np.zeros(len(t_eval), dtype=np.float64)

    n_steps = len(t_eval)
    for i in range(n_steps):
        r = float(r_eval[i])
        l = float(l_eval[i])
        n = float(n_eval[i])

        e = r - (y + n)

        u, integral, filtered_prev = kernel(
            e,
            e_prev,
            filtered_prev,
            integral,
            dt,
            u_min,
            u_max,
            controller_param,
            anti_windup_method,
            ka
        )

        if use_du_dt:
            # Windowed finite-difference estimate of |du/dt|. Using m > 1
            # smooths single-step spikes while preserving the du/dt semantics.
            u_hist[i] = u
            if i >= window_steps:
                du_dt_abs = abs(u - u_hist[i - window_steps]) / window_dt
                if du_dt_abs > max_du_dt:
                    max_du_dt = du_dt_abs

        x, y, y_out = plant_step(A, B, C, D, x, u, l, n, dt, solver)

        if i > 0:
            err = r - y_out
            if performance_index == PerformanceIndexInt.IAE:
                perf += abs(err) * dt
            elif performance_index == PerformanceIndexInt.ISE:
                perf += err * err * dt
            elif performance_index == PerformanceIndexInt.ITAE:
                perf += t_eval[i] * abs(err) * dt
            elif performance_index == PerformanceIndexInt.ITSE:
                perf += t_eval[i] * err * err * dt

        if use_ov and overshoot_step_amplitude_abs > 0.0 and i >= overshoot_step_start_idx:
            signed_overshoot = overshoot_step_sign * (y_out - overshoot_r_final)
            if signed_overshoot > max_overshoot:
                max_overshoot = signed_overshoot

        e_prev = e

    if (not use_ov) or overshoot_step_amplitude_abs <= 0.0:
        overshoot_pct = np.nan
    else:
        if overshoot_step_start_idx < n_steps:
            if max_overshoot > 0.0:
                overshoot_pct = 100.0 * max_overshoot / overshoot_step_amplitude_abs
            else:
                overshoot_pct = 0.0
        else:
            overshoot_pct = np.inf

    return perf, overshoot_pct, max_du_dt


# =============================================================================
# PSO Function
# =============================================================================
@njit(parallel=True)
def time_domain_pso_func(
        kernel,
        controller_param: np.ndarray,
        t_eval: np.ndarray,
        dt: float,
        r_eval:
        np.ndarray,
        l_eval: np.ndarray,
        n_eval: np.ndarray,
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: float,
        system_order: int,
        control_constraint: np.ndarray,
        anti_windup_method: int,
        ka: float,
        solver: int,
        performance_index: int,
        use_overshoot_control: int,
        overshoot_step_amplitude_abs: float,
        overshoot_step_start_idx: int,
        overshoot_step_sign: float,
        overshoot_r_final: float,
        calculate_max_du_dt: int,
        du_dt_window_steps: int,
        swarm_size: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:

    performance_index_val = np.zeros(swarm_size)
    overshoot_pct = np.full(swarm_size, np.nan)
    max_du_dt = np.full(swarm_size, np.nan)

    for i in prange(swarm_size):
        x = np.zeros(system_order, dtype=np.float64)

        perf_i, overshoot_i, max_du_dt_i = simulate_metrics(
            kernel,
            controller_param[i, :],
            t_eval,
            dt,
            r_eval,
            l_eval,
            n_eval,
            x,
            control_constraint,
            anti_windup_method,
            ka,
            A,
            B,
            C,
            D,
            solver,
            performance_index,
            use_overshoot_control,
            overshoot_step_amplitude_abs,
            overshoot_step_start_idx,
            overshoot_step_sign,
            overshoot_r_final,
            calculate_max_du_dt,
            du_dt_window_steps,
        )
        performance_index_val[i] = perf_i
        overshoot_pct[i] = overshoot_i
        max_du_dt[i] = max_du_dt_i

    return performance_index_val, overshoot_pct, max_du_dt


# =============================================================================
# Controller Registry
# =============================================================================
class ControllerSpec:
    def __init__(self, kernel):
        self.kernel = kernel


CONTROLLER_REGISTRY = {
    ControllerType.PID: ControllerSpec(kernel=pid_kernel)
}
