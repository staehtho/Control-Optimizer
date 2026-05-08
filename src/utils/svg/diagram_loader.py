from __future__ import annotations

from typing import Callable

from utils.svg import recolor_svg
from app_domain.controlsys import AntiWindup
from .svg_primitives import SvgData, SVG_STYLE
from .controller_builders import ControllerBuilder

CONTROLLER_SVG_SIZE = (1300, 650)
CLOSED_LOOP_SVG_SIZE = (1900, 800)


def create_svg(size: tuple[int, int], elements: list[SvgData]) -> str:
    """Assemble a list of SvgData elements into a complete SVG document."""
    width, height = size
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 -{height / 4} {width / 2} {height / 2}">'
    )
    svg += SVG_STYLE
    for element in elements:
        svg += (
            f'<g transform="translate({element.translate[0]},'
            f'{element.translate[1]}) rotate({element.rotate})">'
            f'{element.inline_svg}</g>'
        )

    svg += "</svg>"
    return svg


def load_controller_diagram(
        build_controller_svg: Callable[[AntiWindup, tuple[float, float]], list[SvgData]],
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
        color_map: dict[str, str],
) -> str:
    """Build and return the SVG for a controller block diagram."""
    elements = build_controller_svg(anti_windup, constraint)
    svg = create_svg(CONTROLLER_SVG_SIZE, elements)
    recolored_svg = recolor_svg(svg, color_map)
    return recolored_svg


def load_closed_loop_diagram(
        build_closed_loop_svg: Callable[[ControllerBuilder, AntiWindup, tuple[float, float]], list[SvgData]],
        build_controller_svg: ControllerBuilder,
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
        color_map: dict[str, str] | None = None,
) -> str:
    """Build and return the SVG for a full closed-loop system diagram."""
    elements = build_closed_loop_svg(build_controller_svg, anti_windup, constraint)
    svg = create_svg(CLOSED_LOOP_SVG_SIZE, elements)

    if color_map is not None:
        svg = recolor_svg(svg, color_map)

    return svg
