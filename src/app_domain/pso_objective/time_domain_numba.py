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
from numba import njit, prange, float64, int64
from app_domain.controlsys.enums import ControllerType, PerformanceIndexInt, AntiWindupInt, MySolverInt

# State indices
STATE_E_PREV = 0
STATE_INTEGRAL = 1
STATE_D_FILTERED = 2

N_CONTROLLER_STATE = 3  # base layout for PI/PID


@njit
def init_controller_state(n_controllers: int) -> np.ndarray:
    """
    Allocate and initialize controller state array.

    state[i, STATE_E_PREV]    = previous error
    state[i, STATE_INTEGRAL]  = integral state x_I
    state[i, STATE_D_FILTERED]= filtered derivative state
    """
    return np.zeros((n_controllers, N_CONTROLLER_STATE), dtype=np.float64)


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


# *****************************************************************************
# Implementation Controller Step
# *****************************************************************************

# =============================================================================
# PI Update
# =============================================================================
@njit(inline="always")
def pi_step(
        state: np.ndarray,
        i: int,
        e: float,
        dt: float,
        controller_param: np.ndarray,  # [Kp, Ti]
        u_min: float,
        u_max: float,
        anti_windup_method: int,
        ka: float,
) -> float:
    """
    ISA-form PI with anti-windup, operating on flat state array.

    state[i, :] layout:
        0: e_prev        (kept for signature symmetry / future use)
        1: integral x_I  (unscaled ISA integral state)
        2: d_filtered    (unused for PI, kept for compatibility)
    """
    Kp = controller_param[0]
    Ti = controller_param[1]

    # Load state into locals
    integral_prev = state[i, STATE_INTEGRAL]

    # 1) Proportional
    P_term = Kp * e

    # 2) Integration (unscaled ISA state x_I)
    if Ti > 0.0:
        integral_candidate = integral_prev + e * dt
        I_term_prev = (Kp / Ti) * integral_prev
        I_term_candidate = (Kp / Ti) * integral_candidate
    else:
        integral_candidate = integral_prev
        I_term_prev = 0.0
        I_term_candidate = 0.0

    # 3) Unsaturated signals
    u_unsat_prev = P_term + I_term_prev
    u_unsat_candidate = P_term + I_term_candidate

    # 4) Anti-windup
    if anti_windup_method == AntiWindupInt.CONDITIONAL:
        if ((u_min < u_unsat_candidate < u_max) or
                (u_unsat_candidate >= u_max and e < 0.0) or
                (u_unsat_candidate <= u_min and e > 0.0)):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_prev

    elif anti_windup_method == AntiWindupInt.CLAMPING:
        if ((u_min < I_term_candidate < u_max) or
                (I_term_candidate >= u_max and e < 0.0) or
                (I_term_candidate <= u_min and e > 0.0)):
            integral_updated = integral_candidate
            u_unsat_updated = u_unsat_candidate
        else:
            integral_updated = integral_prev
            u_unsat_updated = u_unsat_prev

    elif anti_windup_method == AntiWindupInt.BACKCALCULATION:
        # Saturate candidate
        if u_unsat_candidate > u_max:
            u_sat_candidate = u_max
        elif u_unsat_candidate < u_min:
            u_sat_candidate = u_min
        else:
            u_sat_candidate = u_unsat_candidate

        # Back-calculation on unscaled integral state x_I
        if Ti > 0.0 and Kp != 0.0:
            integral_updated = (
                    integral_candidate
                    + dt * ka * (Ti / Kp) * (u_sat_candidate - u_unsat_candidate)
            )
        else:
            integral_updated = integral_candidate

        if Ti > 0.0:
            I_term_updated = (Kp / Ti) * integral_updated
        else:
            I_term_updated = 0.0

        u_unsat_updated = P_term + I_term_updated

    else:
        integral_updated = 0.0
        u_unsat_updated = 0.0

    # 5) Saturation
    if u_unsat_updated > u_max:
        u = u_max
    elif u_unsat_updated < u_min:
        u = u_min
    else:
        u = u_unsat_updated

    # Write back state in-place
    state[i, STATE_INTEGRAL] = integral_updated

    return u


# =============================================================================
# PID Update
# =============================================================================
@njit(inline="always")
def pid_step(
        state: np.ndarray,
        i: int,
        e: float,
        dt: float,
        controller_param: np.ndarray,  # [Kp, Ti, Td, Tf]
        u_min: float,
        u_max: float,
        anti_windup_method: int,
        ka: float,
) -> float:
    """
    ISA-form PID with filtered derivative and anti-windup, operating on flat state array.

    state[i, :] layout:
        0: e_prev
        1: integral x_I
        2: d_filtered
    """
    Kp = controller_param[0]
    Ti = controller_param[1]
    Td = controller_param[2]
    Tf = controller_param[3]

    # Load state into locals
    e_prev = state[i, STATE_E_PREV]
    integral_prev = state[i, STATE_INTEGRAL]
    d_filtered_prev = state[i, STATE_D_FILTERED]

    # 1) Proportional
    P_term = Kp * e

    # 2) Integration (unscaled ISA state x_I)
    if Ti > 0.0:
        integral_candidate = integral_prev + e * dt
        I_term_previous = Kp * (1.0 / Ti) * integral_prev
        I_term_candidate = Kp * (1.0 / Ti) * integral_candidate
    else:
        integral_candidate = integral_prev
        I_term_previous = 0.0
        I_term_candidate = 0.0

    # 3) Derivative (filtered)
    if Td > 0.0:
        alpha = Tf / (Tf + dt)
        d_filtered_updated = alpha * d_filtered_prev + (1.0 - alpha) * ((e - e_prev) / dt)
    else:
        d_filtered_updated = 0.0

    D_term = Kp * Td * d_filtered_updated

    # 4) Unsaturated u
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
        u_sat_candidate = u_unsat_candidate
        if u_sat_candidate > u_max:
            u_sat_candidate = u_max
        elif u_sat_candidate < u_min:
            u_sat_candidate = u_min

        if Ti > 0.0 and Kp != 0.0:
            integral_updated = integral_candidate + dt * ka * (Ti / Kp) * (u_sat_candidate - u_unsat_candidate)
        else:
            integral_updated = integral_candidate

        if Ti > 0.0:
            I_term_updated = Kp * (1.0 / Ti) * integral_updated
        else:
            I_term_updated = 0.0

        u_unsat_updated = P_term + I_term_updated + D_term

    else:
        integral_updated = 0.0
        u_unsat_updated = 0.0

    # 6) Saturation
    if u_unsat_updated > u_max:
        u = u_max
    elif u_unsat_updated < u_min:
        u = u_min
    else:
        u = u_unsat_updated

    # Write back state in-place
    state[i, STATE_E_PREV] = e
    state[i, STATE_INTEGRAL] = integral_updated
    state[i, STATE_D_FILTERED] = d_filtered_updated

    return u


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
@njit
def system_response_closed_loop(
        step_fn,
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
) -> tuple[np.ndarray, np.ndarray]:
    """
    Simulate a SISO system under PID control with reference and two disturbances (Z1, Z2).

    The function advances the plant state and controller states over `t_eval` and
    returns both the control signal history and the measured output trajectory.

    Args:
        step_fn: Simulation kernel.
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
    n_steps = t_eval.shape[0]
    u_hist = np.zeros(n_steps, dtype=np.float64)
    y_hist = np.zeros(n_steps, dtype=np.float64)

    # Single controller → state shape (1, N_CONTROLLER_STATE)
    state = init_controller_state(1)

    u_min = float(control_constraint[0])
    u_max = float(control_constraint[1])

    # initial output
    y = dot1D(C, x)

    for k in range(n_steps):
        r = float(r_eval[k])
        l = float(l_eval[k])
        n = float(n_eval[k])

        e = r - (y + n)

        # In-place controller update, only u is returned
        u = step_fn(
            state,
            0,  # controller index
            e,
            dt,
            controller_param,
            u_min,
            u_max,
            anti_windup_method,
            ka,
        )

        if np.isnan(u):
            return np.ones_like(t_eval) * np.inf, np.ones_like(t_eval) * np.inf

        x, y, y_out = plant_step(A, B, C, D, x, u, l, n, dt, solver)

        u_hist[k] = u
        y_hist[k] = y_out

    return u_hist, y_hist


# =============================================================================
# PSO helper
# =============================================================================
@njit(inline="always")
def simulate_metrics(
        step_fn,
        state: np.ndarray,
        idx: int,
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
    is applied in the internal controller update step.

    One time-domain simulation for a single particle/controller.

    Uses shared state array:
        state[idx, :] = [e_prev, integral, d_filtered, ...]

    Returns:
        tuple[float, float, float]:
            ``(performance_index_value, overshoot_pct, max_du_dt)``

        ``max_du_dt`` is computed only when ``calculate_max_du_dt`` is enabled.
        It represents the maximum absolute finite-difference control-rate
        estimate over a sliding window of ``du_dt_window_steps`` samples:
        ``max(|u[k] - u[k-m]| / (m * dt))`` with ``m = du_dt_window_steps``.

    """
    # IMPORTANT: do NOT allocate state here; it is shared and indexed by `idx`
    # state shape is (swarm_size, N_CONTROLLER_STATE)

    # Reset this controller's state row
    for j in range(N_CONTROLLER_STATE):
        state[idx, j] = 0.0

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
        u_hist = np.zeros(t_eval.shape[0], dtype=np.float64)

    n_steps = t_eval.shape[0]
    for i in range(n_steps):
        r = float(r_eval[i])
        l = float(l_eval[i])
        n = float(n_eval[i])

        e = r - (y + n)

        u = step_fn(
            state,
            idx,  # controller index into shared state
            e,
            dt,
            controller_param,
            u_min,
            u_max,
            anti_windup_method,
            ka,
        )

        if use_du_dt:
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
        step_fn,
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
    performance_index_val = np.zeros(swarm_size, dtype=np.float64)
    overshoot_pct = np.full(swarm_size, np.nan, dtype=np.float64)
    max_du_dt = np.full(swarm_size, np.nan, dtype=np.float64)

    # Shared controller state for all particles
    state = init_controller_state(swarm_size)
    x = np.zeros((swarm_size, system_order), dtype=np.float64)

    for i in prange(swarm_size):
        perf_i, overshoot_i, max_du_dt_i = simulate_metrics(
            step_fn,
            state,
            i,  # index into state
            controller_param[i, :],  # parameters for this particle
            t_eval,
            dt,
            r_eval,
            l_eval,
            n_eval,
            x[i, :],
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
    def __init__(self, step_fn):
        self.step_fn = step_fn


CONTROLLER_REGISTRY = {
    ControllerType.PI: ControllerSpec(step_fn=pi_step),
    ControllerType.PID: ControllerSpec(step_fn=pid_step),
}
