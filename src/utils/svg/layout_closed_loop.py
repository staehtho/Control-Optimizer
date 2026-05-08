from __future__ import annotations

from app_domain.controlsys import AntiWindup
from .svg_primitives import SvgData, build_path, node, param_block, sum_configurator
from .controller_builders import ControllerBuilder


def closed_loop_builder_svg(
        controller_builder_svg: ControllerBuilder,
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
) -> list[SvgData]:
    """Construct the closed-loop diagram elements."""
    elements = controller_builder_svg(anti_windup, constraint)

    # move the controller to the right
    for element in elements:
        element.translate = (element.translate[0] + 100, element.translate[1])

    elements.extend(
        [
            build_path(0, 0, 85, "horizontal", label="r"),
            sum_configurator(95, 0, south="minus", west="plus"),
            param_block(750, 0, "G(s)", 50, 100),
            build_path(850, 0, 100, "horizontal", "end", "y"),
            node(900, 0),
            build_path(900, 0, 176, "vertical"),
            build_path(95, 10, 166, "vertical"),
            build_path(95, 175, 805, "horizontal"),
        ]
    )

    return elements


def ff_closed_loop_builder_svg(
        controller_builder_svg: ControllerBuilder,
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
) -> list[SvgData]:
    """Construct the closed-loop diagram elements."""
    elements = controller_builder_svg(anti_windup, constraint)

    elements = [el for el in elements if el.tag not in {"kff_r"}]

    # move the controller to the right
    for element in elements:
        element.translate = (element.translate[0] + 100, element.translate[1])

    elements.extend(
        [
            build_path(0, 0, 85, "horizontal", label="r"),
            sum_configurator(95, 0, south="minus", west="plus"),
            param_block(750, 0, "G(s)", 50, 100),
            build_path(850, 0, 100, "horizontal", "end", "y"),
            node(900, 0),
            build_path(900, 0, 176, "vertical"),
            build_path(95, 10, 166, "vertical"),
            build_path(95, 175, 805, "horizontal"),

            # Feed-forward branch
            node(65, 0),
            build_path(65, 0, -126, "vertical"),
            build_path(65, -125, 85, "horizontal", "end"),
        ]
    )

    return elements
