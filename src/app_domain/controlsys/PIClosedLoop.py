from typing import Callable

import numpy as np

from .closedLoop import ClosedLoop
from .enums import AntiWindup, ControllerType
from .plant import Plant


class PIClosedLoop(ClosedLoop):
    controller_type = ControllerType.PI
    has_integrator = True

    def __init__(
            self,
            plant: Plant,
            Kp: float = 0,
            Ti: float = 0,
            control_constraint: list[float] = None,
            anti_windup_method: AntiWindup = AntiWindup.CLAMPING,
            ka: float = 1.0
    ) -> None:
        super().__init__(plant, control_constraint, anti_windup_method, ka)
        self._kp = Kp
        self._ti = Ti

    def get_controller_params(self) -> list[float]:
        return [self._kp, self._ti]

    @staticmethod
    def _controller_formula(Kp: np.ndarray, Ti: np.ndarray, s: np.ndarray) -> np.ndarray:
        return Kp * (1 + 1 / (Ti * s))

    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        s_arr = np.atleast_1d(s)
        Kp = np.array([[self._kp]])
        Ti = np.array([[self._ti]])

        C = self._controller_formula(Kp, Ti, s_arr[None, :])

        return C[0, 0] if np.isscalar(s) else C[0]

    @classmethod
    def frf_batch(
            cls,
            plant_tf: Callable[[np.ndarray | complex], np.ndarray | complex],
            X: np.ndarray,
            s: np.ndarray
    ) -> np.ndarray:
        Kp = X[:, 0][:, None]
        Ti = X[:, 1][:, None]
        s_row = s[None, :]

        G = np.array(plant_tf(s_row)).reshape(-1)

        C = cls._controller_formula(Kp, Ti, s_row)

        return C * G[None, :]
