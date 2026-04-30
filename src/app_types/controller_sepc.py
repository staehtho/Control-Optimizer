from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from dataclasses import dataclass

from app_domain.controlsys import ControllerType, PIClosedLoop, PIDClosedLoop
import resources.blockdiagram as bd

if TYPE_CHECKING:
    from app_domain.controlsys import AntiWindup, ClosedLoop

type SvgData = tuple[str, tuple[int, int]]


class BaseControllerSpec:
    """
    Specification container for a controller type.

    This class defines the metadata required to describe a controller in a
    controller‑agnostic and UI‑agnostic way. Subclasses provide concrete
    specifications such as parameter names, bounds, transfer‑function formulas,
    and SVG rendering logic. The specification is used by the controller
    registry, ViewModels, PSO configuration, and dynamic UI generation.

    Attributes:
        controller_type (ControllerType):
            Enum value identifying the controller family (e.g., PID, PI, PD).
            Used by the controller registry, ViewModels, and UI routing logic
            to select the correct specification and parameter mapping.

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
            The parameter names MUST exactly match the attribute names expected by
            the corresponding controller implementation. Spelling and letter case
            must be identical (e.g., "Kp", "Ti", "Td", "Tf").

        min_bounds (list[float]):
            Hard lower limits for each controller parameter. These represent
            absolute constraints (e.g., positivity) and are used for validation
            and safety checks.

        bounds (tuple[list[float], list[float]]):
            Tuple ``(lower_bounds, upper_bounds)`` defining the optimization
            bounds for PSO. Each list must match the length of ``param_names``.
            These bounds define the feasible search region for tuning.

        transfer_function (str):
            Human‑readable mathematical representation of the controller's
            transfer function, typically expressed as a LaTeX‑compatible string.
            Used for UI display, documentation, and tooltips. The formula must
            correspond exactly to the controller implementation and parameter
            naming.

        build_svg (Callable[[AntiWindup], list[SvgData]]):
            Callable that constructs the SVG block‑diagram representation of the
            controller. The function receives the selected anti‑windup strategy
            and returns a list of positioned SVG elements. Used by the UI to
            render controller diagrams dynamically.

        has_filter_time_constant (bool):
            Indicates whether the controller includes a filter time constant
            (e.g., Tf in PID controllers). Used by the UI to conditionally
            enable, disable, or hide the corresponding parameter field without
            altering layout structure.
    """

    controller_type: ControllerType
    controller_class: type[ClosedLoop]
    param_names: list[str]
    min_bounds: list[float]
    bounds: tuple[list[float], list[float]]
    transfer_function: str
    build_svg: Callable[[AntiWindup], list[SvgData]]
    has_filter_time_constant: bool


@dataclass
class PIDControllerSpec(BaseControllerSpec):
    controller_type = ControllerType.PID
    controller_class = PIDClosedLoop
    param_names = ["Kp", "Ti", "Td"]
    min_bounds = [0.0, 1e-9, 0.0]
    bounds = ([0.0, 0.001, 0.0], [10.0, 10.0, 10.0])
    transfer_function = r"C(s) = K_p \frac{(T_i\, s + 1)(T_d\, s + 1)}{T_i\, s (T_f\, s + 1)}"
    build_svg = staticmethod(bd.get_pid_controller_svg)
    has_filter_time_constant = True


@dataclass
class PIControllerSpec(BaseControllerSpec):
    controller_type = ControllerType.PI
    controller_class = PIClosedLoop
    param_names = ["Kp", "Ti"]
    min_bounds = [0.0, 1e-9]
    bounds = ([0.0, 0.001], [10.0, 10.0])
    transfer_function = r"C(s) = K_p \left(1 + \frac{1}{T_i\, s}\right)"
    build_svg = staticmethod(bd.get_pi_controller_svg)
    has_filter_time_constant = False


CONTROLLER_SPECS = {
    ControllerType.PI: PIControllerSpec,
    ControllerType.PID: PIDControllerSpec,
}
