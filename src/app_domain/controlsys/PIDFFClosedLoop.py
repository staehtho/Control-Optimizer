import numpy as np

from .closedLoop import ClosedLoop
from .enums import AntiWindup, ControllerType
from .plant import Plant


class PIDFFClosedLoop(ClosedLoop):
    controller_type = ControllerType.PID_FF

    def __init__(
            self,
            plant: Plant,
            control_constraint: list[float] = None,
            anti_windup_method: AntiWindup = AntiWindup.CLAMPING,
            ka: float = 1.0
    ) -> None:
        super().__init__(plant, control_constraint, anti_windup_method, ka)
        # TODO params?

    def get_controller_params(self) -> list[float]:
        raise NotImplementedError

    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        raise NotImplementedError
        X = np.array([[self._kp, self._ti, self._td, self._tf]])
        return self.frf_batch(X, np.atleast_1d(s))[0]

    @classmethod
    def transfer_function(cls, s: complex | np.ndarray, **params) -> complex | np.ndarray:
        raise NotImplementedError
        X = np.array([[params["Kp"], params["Ti"], params["Td"], params["Tf"]]])
        return cls.frf_batch(X, np.atleast_1d(s))[0]

    @classmethod
    def frf_batch(cls, X: np.ndarray, s: np.ndarray) -> np.ndarray:
        raise NotImplementedError
