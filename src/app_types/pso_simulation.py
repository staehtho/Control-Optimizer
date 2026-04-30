from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass


if TYPE_CHECKING:
    from app_types import BaseControllerSpec
    from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex, MySolver
    from app_domain.functions import BaseFunction


@dataclass
class PsoHyperparameters:
    randomness: float
    u1: float
    u2: float
    initial_range: tuple[float, float]
    initial_swarm_span: int
    min_neighbors_fraction: float
    max_stall: int
    max_iter: int
    stall_windows_required: int
    space_factor: float
    convergence_factor: float


@dataclass
class PsoSimulationParam:
    """Parameter container for PSO-based PID optimization."""

    num: list[float]
    den: list[float]

    controller_spec: BaseControllerSpec

    t0: float
    t1: float
    dt: float

    tuning_factor: float
    limit_factor: float
    sampling_rate: float | None

    solver: MySolver

    anti_windup: AntiWindup
    constraint: tuple[float, float]
    ka: float

    excitation_target: ExcitationTarget
    function: BaseFunction

    bounds: tuple[list[float], list[float]]
    n_param: int

    swarm_size: int
    pso_iteration: int

    error_criterion: PerformanceIndex
    overshoot_control: float
    overshoot_control_enabled: bool
    slew_rate_max: float
    slew_window_size: int
    slew_rate_limit_enabled: bool
    gain_margin: float
    gain_margin_enabled: bool
    phase_margin: float
    phase_margin_enabled: bool
    stability_margin: float
    stability_margin_enabled: bool

    omega_exp_low: int
    omega_exp_high: int
    omega_points: int

    hyperparameters: PsoHyperparameters


@dataclass
class PsoResult:
    """Result container for optimized PID parameters."""

    simulation_time: float

    best_params: dict[str, float]
    has_tf: bool
    tf_limited_simulation: bool
    tf_limited_sampling: bool
    min_sampling_rate: float

    t0: float
    t1: float

    is_feasible: bool
    error_criterion: float
    overshoot: float
    show_overshoot: bool
    slew_rate: float
    gain_margin: float
    omega_180: float
    has_omega_180: bool
    phase_margin: float
    omega_c: float
    has_omega_c: bool
    stability_margin: float
