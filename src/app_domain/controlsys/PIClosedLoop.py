import numpy as np

from .closedLoop import ClosedLoop
from .enums import AntiWindup, ControllerType
from .plant import Plant


class PIClosedLoop(ClosedLoop):
    controller_type = ControllerType.PI

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

    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        X = np.array([[self._kp, self._ti]])
        return self.frf_batch(X, np.atleast_1d(s))[0]

    @classmethod
    def transfer_function(cls, s: complex | np.ndarray, **params) -> complex | np.ndarray:
        X = np.array([[params["Kp"], params["Ti"]]])
        return cls.frf_batch(X, np.atleast_1d(s))[0]

    @classmethod
    def frf_batch(cls, X: np.ndarray, s: np.ndarray) -> np.ndarray:
        """Vectorized frequency response (core implementation)."""
        with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
            Kp = X[:, 0][:, None]
            Ti = X[:, 1][:, None]
            s_row = s[None, :]
            return Kp * (1 + 1 / (Ti * s_row))
