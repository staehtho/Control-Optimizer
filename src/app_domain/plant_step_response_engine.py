from numpy import ndarray

from .controlsys import Plant, MySolver


class PlantStepResponseEngine:
    @staticmethod
    def compute(num: list[float], den: list[float], t0: float, t1: float, solver: MySolver) -> tuple[ndarray, ndarray]:

        dt = (t1 - t0) / 5000
        plant = Plant(num, den)

        t, y = plant.step_response(t0, t1, dt, solver)

        return t, y