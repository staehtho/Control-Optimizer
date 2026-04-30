from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from dataclasses import dataclass

from app_domain.controlsys import ControllerType, PIClosedLoop, PIDClosedLoop, PIDFFClosedLoop
import resources.blockdiagram as bd

if TYPE_CHECKING:
    from app_domain.controlsys import AntiWindup, ClosedLoop

type SvgData = tuple[str, tuple[int, int]]


class BaseControllerSpec:
    """
    Specification container for a controller type.

    This class defines the metadata required to describe a controller in a
    controller‑agnostic and UI‑agnostic way. Subclasses provide concrete
    specifications such as parameter names, bounds, and SVG rendering logic.
    The specification is used by the controller registry, ViewModels, PSO
    configuration, and dynamic UI generation.

    Attributes:
        controller_class (type[ClosedLoop]):
            The ClosedLoop subclass implementing the controller's time- and
            frequency-domain behavior. Used to instantiate the controller
            and access its simulation methods.

        param_names (list[str]):
            Ordered list of controller parameter names. These names define the
            canonical order in which parameters appear in:
                - PSO parameter vectors
                - UI parameter fields
                - FRF batch matrices
                - controller parameter dictionaries
            The parameter names MUST exactly match the attribute names expected by the
            corresponding controller implementation. The spelling and letter case are
            significant and must be identical to the names used in the controller
            class (e.g., "Kp", "Ti", "Td", "Tf"). Mismatched or incorrectly cased
            names will lead to incorrect parameter mapping and runtime errors.

        min_bounds (list[float]):
            Hard lower limits for each controller parameter. These represent
            absolute constraints (e.g., positivity) and are used for validation
            and safety checks.

        bounds (tuple[list[float], list[float]]):
            Tuple ``(lower_bounds, upper_bounds)`` defining the optimization
            bounds for PSO. Each list must match the length of ``param_names``.
            These bounds are controller‑specific and define the feasible search
            region for tuning.

        transfer_function (str):
            Human‑readable mathematical representation of the controller's
            transfer function, typically expressed as a LaTeX‑compatible string.
            This is used for UI display, documentation, and tooltips. The formula
            must correspond exactly to the controller implementation and parameter
            naming.

        build_svg (Callable[[AntiWindup], list[SvgData]]):
            Callable that constructs the SVG block‑diagram representation of the
            controller. The function receives the selected anti‑windup strategy
            and returns a list of positioned SVG elements. Used by the UI to
            render controller diagrams dynamically.
    """

    controller_class: type[ClosedLoop]
    param_names: list[str]
    min_bounds: list[float]
    bounds: tuple[list[float], list[float]]
    transfer_function: str
    build_svg: Callable[[AntiWindup], list[SvgData]]


@dataclass
class PIDControllerSpec(BaseControllerSpec):
    controller_class = PIDClosedLoop
    param_names = ["Kp", "Ti", "Td"]
    min_bounds = [0.0, 1e-9, 0.0]
    bounds = ([0.0, 0.001, 0.0], [10.0, 10.0, 10.0])
    transfer_function = r"C(s) = K_p \frac{(T_i\, s + 1)(T_d\, s + 1)}{T_i\, s (T_f\, s + 1)}"
    build_svg = staticmethod(bd.get_pid_controller_svg)


@dataclass
class PIControllerSpec(BaseControllerSpec):
    controller_class = PIClosedLoop
    param_names = ["Kp", "Ti"]
    min_bounds = [0.0, 1e-9]
    bounds = ([0.0, 0.001], [10.0, 10.0])
    transfer_function = r"C(s) = K_p \left(1 + \frac{1}{T_i\, s}\right)"
    build_svg = staticmethod(bd.get_pi_controller_svg)


@dataclass
class PIDFFControllerSpec(BaseControllerSpec):
    controller_class = PIDFFClosedLoop
    # TODO: params?
    param_names = ["ab", "cd"]
    min_bounds = [5.0, 5.0]
    bounds = ([5.0, 5.0], [20.0, 30.0])
    transfer_function = ""
    build_svg = staticmethod(bd.get_pid_ff_controller_svg)


CONTROLLER_SPECS = {
    ControllerType.PI: PIControllerSpec,
    ControllerType.PID: PIDControllerSpec,
    ControllerType.PID_FF: PIDFFControllerSpec,
}
