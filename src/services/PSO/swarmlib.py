# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Module:        swarmlib.py
# Description:   Implements a Particle Swarm Optimization (PSO) framework including particle
#                dynamics, swarm management, adaptive neighborhood selection, and convergence
#                criteria. Provides a configurable optimizer capable of evaluating arbitrary
#                objective functions and tracking global and personal best solutions.
#
# Authors:       Florin Büchi, Thomas Stähli
# Created:       01.12.2025
# Modified:      01.12.2025
# Version:       1.0
#
# License:       ZHAW Zürcher Hochschule für angewandte Wissenschaften (or internal use only)
# ──────────────────────────────────────────────────────────────────────────────


import copy
import math
import random
import sys
from typing import Callable, List, Optional

import numpy as np


# ============================================================================
# Particle class
# ============================================================================
class Particle:
    """Represents a single particle in the swarm.

    Each particle keeps track of its position, velocity, current cost, and personal best.
    Class-level attributes store global parameters shared among all particles.
    """

    # Class-level (shared) attributes
    bounds: np.ndarray
    coefficients: List[float]  # [inertia, cognitive_coeff, social_coeff]
    randomness: float = 1.0
    speed_bounds: np.ndarray

    # -------------------------------------------------------------------------
    # Instance-level attributes
    # -------------------------------------------------------------------------
    def __init__(self, position: np.ndarray, velocity: np.ndarray) -> None:
        """Initializes a particle with a position and velocity.

        Args:
            position (np.ndarray): Initial position vector of the particle.
            velocity (np.ndarray): Initial velocity vector of the particle.
        """
        self._position = position
        self._velocity = velocity
        self._cost: float = sys.float_info.max
        self._p_best_cost: float = sys.float_info.max
        self._p_best_position: np.ndarray = position

    # -------------------------------------------------------------------------
    # Class configuration
    # -------------------------------------------------------------------------
    @classmethod
    def configure_class(cls,
                        bounds: np.ndarray,
                        coefficients: List[float],
                        randomness: float) -> None:
        """Configures shared parameters for all particles.

        Args:
            bounds (np.ndarray): Global bounds for all particles.
            coefficients (List[float]): List of coefficients [inertia, c1, c2].
            randomness (float): Random factor for velocity update.
        """
        cls.bounds = bounds
        cls.coefficients = coefficients
        cls.randomness = randomness
        r = np.subtract(bounds[1], bounds[0])
        cls.speed_bounds = np.array([-r, r]).T  # velocity limits per dimension

    # -------------------------------------------------------------------------
    # Attributes
    # -------------------------------------------------------------------------

    @property
    def position(self) -> np.ndarray:
        return self._position

    @property
    def p_best_cost(self) -> float:
        return self._p_best_cost

    @property
    def p_best_position(self) -> np.ndarray:
        return self._p_best_position

    # -------------------------------------------------------------------------
    # Particle dynamics
    # -------------------------------------------------------------------------
    def update_velocity(self,
                        swarm_particles: List['Particle'],
                        i: int,
                        N: int) -> None:
        """Updates the particle's velocity based on personal best and neighborhood best.

        Args:
            swarm_particles (List[Particle]): List of all particles in the swarm.
            i (int): Index of this particle in the swarm.
            N (int): Number of neighbors considered for local best.
        """
        # Random factors for stochastic velocity update
        u1 = random.uniform(1.0 - Particle.randomness, 1.0)
        u2 = random.uniform(1.0 - Particle.randomness, 1.0)

        # Select neighborhood indices (exclude self)
        indices = list(range(len(swarm_particles)))
        indices.remove(i)
        neighbors = random.sample(indices, N)
        best_neighbor = min([swarm_particles[j] for j in neighbors],
                            key=lambda pp: pp.p_best_cost)

        # Compute velocity contributions
        vec_g_best = best_neighbor.p_best_position - self._position
        vec_p_best = self._p_best_position - self._position

        inertia, c1, c2 = Particle.coefficients
        self._velocity = (
                self._velocity * inertia
                + vec_g_best * c1 * u1
                + vec_p_best * c2 * u2
        )

        # Clip velocity to bounds
        for j in range(len(self._position)):
            min_v, max_v = Particle.speed_bounds[j]
            self._velocity[j] = np.clip(self._velocity[j], min_v, max_v)

    def update_position(self) -> None:
        """Updates the particle's position based on velocity, enforcing bounds."""
        self._position += self._velocity
        for j in range(len(self._position)):
            if self._position[j] > Particle.bounds[1][j]:
                self._position[j] = Particle.bounds[1][j]
                self._velocity[j] = 0
            elif self._position[j] < Particle.bounds[0][j]:
                self._position[j] = Particle.bounds[0][j]
                self._velocity[j] = 0

    def update_best(self, cost: float) -> None:
        """Updates the personal best position if the current cost is better.

        Args:
            cost (float): Current cost value of the particle.
        """
        self._cost = cost
        if cost < self._p_best_cost:
            self._p_best_cost = cost
            self._p_best_position = copy.deepcopy(self._position)


# ============================================================================
# Swarm class
# ============================================================================
class Swarm:
    """Particle Swarm Optimization (PSO) swarm manager.

    This class manages the entire swarm, including initialization, iteration,
    global best tracking, and convergence criteria.
    """

    def __init__(self,
                 obj_func: Callable[[np.ndarray], np.ndarray],
                 size: int,
                 param_number: int,
                 bounds: List[List[float]],
                 randomness: float = 1.0,
                 u1: float = 1.49,
                 u2: float = 1.49,
                 initial_range: tuple[float, float] = (0.1, 1.1),
                 initial_swarm_span: int = 2000,
                 min_neighbors_fraction: float = 0.25,
                 max_stall: int = 15,
                 space_factor: float = 0.001,
                 convergence_factor: float = 1e-2) -> None:
        """Initializes the PSO swarm with given parameters.

        Args:
            obj_func (Callable[[np.ndarray], np.ndarray]): Objective function.
            size (int): Number of particles in the swarm.
            param_number (int): Number of parameters (dimensions) to optimize.
            bounds (List[List[float]]): Bounds for each parameter [[min, max], ...].
            randomness (float, optional): Random factor for velocity updates. Defaults to 1.0.
            u1 (float, optional): Cognitive coefficient. Defaults to 1.49.
            u2 (float, optional): Social coefficient. Defaults to 1.49.
            initial_range (tuple[float, float], optional): Inertia weight range. Defaults to (0.1, 1.1).
            initial_swarm_span (int, optional): Initial span divisions for particle positions. Defaults to 2000.
            min_neighbors_fraction (float, optional): Minimum fraction of swarm considered neighbors. Defaults to 0.25.
            max_stall (int, optional): Maximum iterations with little improvement. Defaults to 15.
            space_factor (float, optional): Factor to define particle space convergence. Defaults to 0.001.
            convergence_factor (float, optional): Relative change threshold for convergence. Defaults to 1e-2.
        """
        self.obj_func = obj_func
        self.size = size
        self.param_number = param_number
        self.bounds = np.array(bounds, dtype=float)
        self.randomness = randomness
        self._coefficients = [initial_range[1], u1, u2]
        self._initial_range = initial_range
        self._max_stall = max_stall
        self._initial_swarm_span = initial_swarm_span
        self._min_neighbors_fraction = min_neighbors_fraction
        self._space_factor = space_factor
        self._convergence_factor = convergence_factor

        self.particles: List[Particle] = []
        self.gBest: Particle
        self.iterations: int = 0
        self._no_improvement_counter = 0

        # Initialize swarm particles
        self._init_swarm()

    # -------------------------------------------------------------------------
    # Internal initialization
    # -------------------------------------------------------------------------
    def _init_swarm(self) -> None:
        """Initializes particle positions, velocities, and class-level parameters."""
        self.particles.clear()
        self._min_neighborhood_size = max(2, math.floor(self.size * self._min_neighbors_fraction))
        self._N = random.randint(self._min_neighborhood_size, self.size - 1)

        # Compute range and span for initialization
        r = np.subtract(self.bounds[1], self.bounds[0])
        span = r / self._initial_swarm_span

        # Configure shared particle parameters
        Particle.configure_class(
            bounds=self.bounds,
            coefficients=self._coefficients,
            randomness=self.randomness
        )

        # Initialize particles
        for _ in range(self.size):
            position = np.array([
                self.bounds[0][j] + span[j] * random.randint(0, self._initial_swarm_span)
                for j in range(self.param_number)
            ])
            velocity = np.array([random.uniform(-r[j], r[j]) for j in range(self.param_number)])
            self.particles.append(Particle(position, velocity))

        self._init_costs()
        self._init_global_best()

    def _get_costs(self) -> np.ndarray:
        """Evaluates the objective function for all particles.

        Returns:
            np.ndarray: Array of cost values for each particle.
        """
        positions = np.array([p.position for p in self.particles])
        return self.obj_func(positions)

    def _init_costs(self) -> None:
        """Initializes particle costs and personal best positions."""
        costs = self._get_costs()
        for particle, cost in zip(self.particles, costs):
            particle.update_best(cost)

    def _init_global_best(self) -> None:
        """Determines the initial global best particle in the swarm."""
        self.gBest = copy.deepcopy(min(self.particles, key=lambda p: p.p_best_cost))

        # -------------------------------------------------------------------------
        # Iteration
        # -------------------------------------------------------------------------

    def _iterate(self) -> None:
        """Performs a single iteration of the PSO algorithm.

        Updates velocities, positions, personal bests, and global best.
        Dynamically adjusts inertia and neighborhood size based on improvement.
        """
        new_best = False

        # Update velocity and position for all particles
        for i, p in enumerate(self.particles):
            p.update_velocity(self.particles, i, self._N)
            p.update_position()

        # Evaluate costs and update personal/global bests
        costs = self._get_costs()
        for particle, cost in zip(self.particles, costs):
            particle.update_best(cost)
            if particle.p_best_cost < self.gBest.p_best_cost:
                self.gBest = copy.deepcopy(particle)
                new_best = True

        # Adaptive neighborhood and inertia adjustments
        if new_best:
            self._no_improvement_counter = max(0, self._no_improvement_counter - 1)
            self._N = self._min_neighborhood_size
            if self._no_improvement_counter < 2:
                self._coefficients[0] *= 2
            elif self._no_improvement_counter > 5:
                self._coefficients[0] /= 2
            self._coefficients[0] = np.clip(
                self._coefficients[0],
                self._initial_range[0],
                self._initial_range[1]
            )
        else:
            self._no_improvement_counter += 1
            self._N = min(self._N + self._min_neighborhood_size, self.size - 1)

        # -------------------------------------------------------------------------
        # Utility
        # -------------------------------------------------------------------------

    def _get_particle_space(self) -> float:
        """Computes the hypervolume spanned by all particles in parameter space.

        Returns:
            float: Hypervolume spanned by particle positions.
        """
        min_positions = np.min([p.position for p in self.particles], axis=0)
        max_positions = np.max([p.position for p in self.particles], axis=0)
        return np.prod(max_positions - min_positions)

        # -------------------------------------------------------------------------
        # Public API
        # -------------------------------------------------------------------------

    def simulate_swarm(self,
                       iterate_func: Optional[Callable[['Swarm'], None]] = None
                       ) -> tuple[np.ndarray, float]:
        """Runs the Particle Swarm Optimization (PSO) until convergence.

        This method iteratively updates particle positions and velocities
        according to the PSO algorithm, tracking global and personal bests.
        The optimization stops when either the swarm's particle space shrinks
        below a threshold or when improvements stall beyond a defined limit.

        Args:
            iterate_func (Optional[Callable[['Swarm'], None]]):
                An optional callback function executed at each iteration.
                Receives the current swarm instance and can be used for
                logging or monitoring progress.

        Returns:
            tuple[np.ndarray, float]:
                A tuple containing:
                - The best position vector found by the swarm (`np.ndarray`).
                - The corresponding best cost value (`float`).
        """
        swarm_state = [self.gBest.p_best_cost]
        termination_criteria = False
        space_criteria = False

        # Compute initial hypervolume for convergence comparison
        r = np.subtract(self.bounds[1], self.bounds[0])
        initial_space = np.prod(r)

        while True:
            self._iterate()
            self.iterations += 1
            swarm_state.append(self.gBest.p_best_cost)

            particle_space = self._get_particle_space()

            # Execute user-provided callback if available
            if iterate_func:
                iterate_func(self)

            # Check convergence based on particle hypervolume
            if particle_space < initial_space * self._space_factor:
                space_criteria = True
            if space_criteria:
                termination_criteria = True

            # Robust convergence check based on lack of improvement
            if len(swarm_state) > self._max_stall:
                prev_cost = swarm_state[-self._max_stall]
                curr_cost = swarm_state[-1]

                # Falls vorher oder aktuell NaN/inf → setze Verbesserung auf 0
                if not np.isfinite(prev_cost) or not np.isfinite(curr_cost) or prev_cost == 0:
                    improvement = 0.0
                else:
                    improvement = 1 - (curr_cost / prev_cost)

                # Prüfen, ob Verbesserung klein genug ist
                if improvement <= self._convergence_factor:
                    termination_criteria = True

            if termination_criteria:
                break

        return self.gBest.p_best_position, self.gBest.p_best_cost
