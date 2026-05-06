from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from dataclasses import dataclass

from app_domain.controlsys import ControllerType
from app_domain.controlsys.PIClosedLoop import PIClosedLoop
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
import resources.blockdiagram as bd

if TYPE_CHECKING:
    from app_domain.controlsys import AntiWindup, ClosedLoop

type SvgData = tuple[str, tuple[int, int]]


@dataclass(frozen=True)
class ControllerSpec:
    """
    Specification container for a controller type.

    This class defines the metadata required to describe a controller in a
    controller‑agnostic and UI‑agnostic way. Subclasses provide concrete
    specifications. The specification is used by the controller registry,
    ViewModels, PSO configuration, and dynamic UI generation.

    Attributes:
        controller_class (type[ClosedLoop]):
            The ClosedLoop subclass implementing the controller's time‑ and
            frequency‑domain behavior. Used to instantiate the controller
            and access its simulation methods.

        param_names (list[str]):
            Ordered list of controller parameter names. These names define the
            canonical order in which parameters appear in:
                - PSO parameter vectors
                - UI parameter fields
                - FRF batch matrices
                - controller parameter dictionaries
            The parameter names MUST exactly match the attribute names expected by
            the corresponding controller implementation.

        bounds (tuple[list[float], list[float]]):
            Tuple ``(lower_bounds, upper_bounds)`` defining the optimization
            bounds for PSO. Each list must match the length of ``param_names``.
            These bounds define the default search region for tuning.

        build_svg (Callable[[AntiWindup], list[SvgData]]):
            Callable that constructs the SVG block‑diagram representation of the
            controller. The function receives the selected anti‑windup strategy
            and returns a list of positioned SVG elements.

        tf_controller (str):
            Human‑readable mathematical representation of the controller
            transfer function ``C(s)``, typically a LaTeX‑compatible string.
            Must correspond exactly to the controller implementation.

        tf_open_loop (str):
            Human‑readable formula for the open‑loop transfer function

                L(s) = C(s) · G(s)

            Used for UI display, tooltips, and documentation.

        tf_close_loop (str):
            Human‑readable formula for the closed‑loop transfer function

                T(s) = L(s) / (1 + L(s))

            representing the standard unity‑feedback closed‑loop system.

        tf_sensitivity (str):
            Human‑readable formula for the sensitivity function

                S(s) = 1 / (1 + L(s))

            describing disturbance attenuation and robustness.
    """


    controller_class: type[ClosedLoop]
    param_names: list[str]
    bounds: tuple[list[float], list[float]]
    build_svg: Callable[[AntiWindup], list[SvgData]]
    tf_controller: str
    tf_open_loop: str = r"L(s) = C(S) \cdot G(s)"
    tf_close_loop: str = r"T(s) = \frac{L(s)}{1 + L(s)} = \frac{C(s) \cdot G(s)}{1 + C(s) \cdot G(s)}"
    tf_sensitivity: str = r"S(s) = \frac{1}{1 + L(s)} = \frac{1}{1 + C(s) \cdot G(s)}"


pid_spec = ControllerSpec(
    controller_class=PIDClosedLoop,
    param_names=["Kp", "Ti", "Td"],
    bounds=([0.0, 0.001, 0.0], [10.0, 10.0, 10.0]),
    build_svg=bd.get_pid_controller_svg,
    tf_controller=r"C(s) = K_p \frac{(T_i\, s + 1)(T_d\, s + 1)}{T_i\, s (T_f\, s + 1)}",
)

pi_spec = ControllerSpec(
    controller_class=PIClosedLoop,
    param_names=["Kp", "Ti"],
    bounds=([0.0, 0.001], [10.0, 10.0]),
    build_svg=bd.get_pi_controller_svg,
    tf_controller=r"C(s) = K_p \left(1 + \frac{1}{T_i\, s}\right)",
)

CONTROLLER_SPECS = {
    ControllerType.PI: pi_spec,
    ControllerType.PID: pid_spec,
}
