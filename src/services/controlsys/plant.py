# ──────────────────────────────────────────────────────────────────────────────
# Project:       PID Optimizer
# Module:        plant.py
# Description:   Defines the Plant class representing a linear time-invariant system specified
#                by its transfer function. Provides state-space conversion, transfer-function
#                evaluation, dominant time-constant estimation, and utilities for open-loop
#                frequency- and time-domain simulation, including step responses.
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
from scipy.signal import tf2ss

from .enums import map_enum_to_int, MySolver


class Plant:
    """
    Represents a linear time-invariant (LTI) system defined by its transfer function.

    Args:
        num (list[float] | np.ndarray): Numerator coefficients of the transfer function
            in descending powers of s.
        den (list[float] | np.ndarray): Denominator coefficients of the transfer function
            in descending powers of s.

    Example:
        >>> plant = Plant(num=[1], den=[1, 2, 1])
        >>> plant.system(1j)
    """

    def __init__(
            self,
            num: list[float] | np.ndarray,
            den: list[float] | np.ndarray,
            solver: MySolver = MySolver.RK4
    ) -> None:
        self._num = np.array(num, dtype=float)
        self._den = np.array(den, dtype=float)

        self._solver = solver

        # Dominante Zeitkonstante T1 bestimmen
        roots = np.roots(self._den)
        stable_poles = roots[np.real(roots) < 0]
        if stable_poles.size > 0:
            self._t1 = -1 / np.min(np.real(stable_poles))
        else:
            self._t1 = 1.0  # fallback

        # Transfer function to state-space representation.
        self._A: np.ndarray
        self._B: np.ndarray
        self._C: np.ndarray
        self._D: np.ndarray

        self._A, self._B, self._C, self._D = tf2ss(self._num, self._den)

    def __format__(self, format_spec: str) -> str:
        """
        Returns a formatted string representation of the transfer function.

        Args:
            format_spec (str): Format type. Supported values:
                - "plant": MATLAB-style transfer function representation.
                - "num": Numerator coefficients only.
                - "den": Denominator coefficients only.

        Returns:
            str: Formatted transfer function string.

        Raises:
            NotImplementedError: If the format specifier is not supported.

        Example:
            >>> plant = Plant(num=[1], den=[1, 2, 1])
            >>> format(plant, "plant")
            'tf([1], [1 2 1])'
        """
        # Whitespace entfernen und lower() für Sicherheit
        format_spec = format_spec.strip().lower()

        if format_spec == "plant":
            num_str = "[" + " ".join(map(str, self._num)) + "]"
            den_str = "[" + " ".join(map(str, self._den)) + "]"
            return f"tf({num_str}, {den_str})"
        elif format_spec == "num":
            num_str = "[" + " ".join(map(str, self._num)) + "];"
            return num_str
        elif format_spec == "den":
            den_str = "[" + " ".join(map(str, self._den)) + "];"
            return den_str
        else:
            raise NotImplementedError(f"Unsupported format specifier: '{format_spec}'")

    # ******************************
    # Attributes
    # ******************************

    @property
    def num(self) -> np.ndarray:
        """Numerator coefficients of the transfer function."""
        return self._num

    @property
    def den(self) -> np.ndarray:
        """Denominator coefficients of the transfer function."""
        return self._den

    @property
    def t1(self) -> float:
        """Dominant time constant (used for derivative filter)."""
        return self._t1

    @property
    def solver(self) -> MySolver:
        return self._solver

    def get_ABCD(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns the state-space matrices (A, B, C, D) of the system.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
                State-space matrices A, B, C, D as NumPy arrays.
        """
        return (np.array(self._A, dtype=np.float64),
                np.array(self._B, dtype=np.float64),
                np.array(self._C, dtype=np.float64),
                np.array(self._D, dtype=np.float64))

    # ******************************
    # Methods
    # ******************************

    def get_plant_order(self) -> int:
        """
        Returns the order of the plant.

        Returns:
            int: Plant order (number of states).
        """
        return self._A.shape[0]

    def system(self, s: complex | np.ndarray) -> complex | np.ndarray:
        """
        Evaluates the transfer function at a given complex frequency `s`.

        Args:
            s (complex | np.ndarray): Laplace variable (σ + jω). Can be scalar or array.

        Returns:
            complex | np.ndarray: Value of the transfer function at `s`.
            Returns an array of the same shape if `s` is an array.

        Notes:
            - The coefficient arrays are reversed internally to match
              `numpy.polyval`, which expects the highest power first.

        Example:
            >>> plant = Plant(num=[1], den=[1, 2, 1])
            >>> plant.system(1j)
        """
        return np.polyval(self._num, s) / np.polyval(self._den, s)

    def step_response(
            self,
            t0: float = 0,
            t1: float = 10,
            dt: float = 0.01
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Computes the open-loop step response of the plant.

        Args:
            t0 (float): Start time of simulation. Default is 0.
            t1 (float): End time of simulation. Default is 10.
            dt (float): Time step for simulation. Default is 0.01.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                - Time vector (np.ndarray)
                - Output response (np.ndarray)
        """
        u = lambda t: np.ones_like(t)

        return self.system_response(u, t0, t1, dt)

    def system_response(self,
                        u: Callable[[np.ndarray], np.ndarray],
                        t0: float = 0,
                        t1: float = 10,
                        dt: float = 0.01,
                        x0: np.ndarray | None = None
                        ) -> tuple[np.ndarray, np.ndarray]:
        """
        Simulates the system's open-loop time response for a given input signal.

        Args:
            u (Callable[[np.ndarray], np.ndarray]): Input function that takes
                a time vector and returns the corresponding input signal.
            t0 (float): Start time of simulation. Default is 0.
            t1 (float): End time of simulation. Default is 10.
            dt (float): Time step for simulation. Default is 0.01.
            x0 (np.ndarray | None): Optional initial state vector. If None,
                it is initialized to zeros.

        Returns:
            tuple[np.ndarray, np.ndarray]:
                - Time vector (np.ndarray)
                - Plant output trajectory (np.ndarray)
        """
        from .pso_system_optimization import system_response  # local import
        t_eval = np.arange(t0, t1 + dt, dt)
        u_eval = u(t_eval)

        if x0 is None:
            x0 = np.zeros(self.get_plant_order(), dtype=np.float64)

        A = np.ascontiguousarray(self._A, dtype=np.float64)
        B = np.ascontiguousarray(self._B.flatten(), dtype=np.float64)
        C = np.ascontiguousarray(self._C.flatten(), dtype=np.float64)
        D = float(self._D[0, 0])

        y = system_response(
            t_eval=t_eval,
            dt=dt,
            u_eval=u_eval,
            x=x0,
            A=A,
            B=B,
            C=C,
            D=D,
            solver=map_enum_to_int(self._solver)
        )

        return t_eval, np.array(y)

