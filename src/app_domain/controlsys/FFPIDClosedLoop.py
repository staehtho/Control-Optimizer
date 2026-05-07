from typing import Callable

import numpy as np

from .PIDClosedLoop import PIDClosedLoop
from .enums import AntiWindup
from .enums import ControllerType
from .plant import Plant


class FFPIDClosedLoop(PIDClosedLoop):
    controller_type = ControllerType.FFPID
    tf_link_index = 2
    has_integrator = True

    def __init__(
            self,
            plant: Plant,
            *,
            Kp: float = None,
            Ki: float = None,
            Kd: float = None,
            Ti: float = None,
            Td: float = None,
            Kff: float = 0.0,
            Tf: float = 0.01,
            control_constraint: list[float] = None,
            anti_windup_method: AntiWindup = AntiWindup.CLAMPING,
            ka: float = 1.0,
    ) -> None:
        super().__init__(
            plant,
            Kp=Kp,
            Ki=Ki,
            Kd=Kd,
            Ti=Ti,
            Td=Td,
            Tf=Tf,
            control_constraint=control_constraint,
            anti_windup_method=anti_windup_method,
            ka=ka,
        )
        self._kff = float(Kff)

    def get_controller_params(self) -> list[float]:
        return [self._kp, self._ti, self._td, self._kff, self._tf]

    def closed_loop(self, s: complex | np.ndarray) -> complex | np.ndarray:
        c_fb = self.controller(s)
        g = self.plant.system(s)
        return g * (c_fb + self._kff) / (1 + c_fb * g)

    @classmethod
    def frf_batch(
            cls,
            plant_tf: Callable[[np.ndarray | complex], np.ndarray | complex],
            X: np.ndarray,
            s: np.ndarray
    ) -> np.ndarray:
        Kp = X[:, 0][:, None]
        Ti = X[:, 1][:, None]
        Td = X[:, 2][:, None]
        Tf = X[:, 4][:, None]

        s_row = s[None, :]

        G = np.array(plant_tf(s_row)).reshape(-1)
        C = cls._controller_formula(Kp, Ti, Td, Tf, s_row)

        return C * G[None, :]
