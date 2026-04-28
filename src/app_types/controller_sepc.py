from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from dataclasses import dataclass

from app_domain.controlsys import ControllerType, PIDClosedLoop, PIDFFClosedLoop
import resources.blockdiagram as bd

if TYPE_CHECKING:
    from app_domain.controlsys import AntiWindup, ClosedLoop

type SvgData = tuple[str, tuple[int, int]]


class BaseControllerSpec:
    controller_class: type[ClosedLoop]
    param_names: list[str]
    min_bounds: list[float]
    bounds: tuple[list[float], list[float]]
    build_svg: Callable[[AntiWindup], list[SvgData]]


@dataclass
class PIDControllerSpec(BaseControllerSpec):
    controller_class = PIDClosedLoop
    param_names = ["Kp", "Ti", "Td"]
    min_bounds = [0.0, 1e-9, 0.0]
    bounds = ([0.0, 0.001, 0.0], [10.0, 10.0, 10.0])
    build_svg = staticmethod(bd.build_controller_svg_pid)


@dataclass
class PIDFFControllerSpec(BaseControllerSpec):
    controller_class = PIDFFClosedLoop
    # TODO: params?
    param_names = ["ab", "cd"]
    min_bounds = [5.0, 5.0]
    bounds = ([5.0, 5.0], [20.0, 30.0])
    build_svg = staticmethod(bd.build_controller_svg_pid_ff)


CONTROLLER_SPECS = {
    ControllerType.PID: PIDControllerSpec,
    ControllerType.PID_FF: PIDFFControllerSpec,
}
