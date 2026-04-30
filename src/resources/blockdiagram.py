from __future__ import annotations

from typing import Callable

from .resources import BlockDiagram, BLOCK_DIAGRAM_DIR
from utils.svg_utils import SvgLayer, merge_svgs, recolor_svg
from app_domain.controlsys import AntiWindup

type SvgData = tuple[str, tuple[int, int]]


def load_controller_diagram(
        build_controller_svg: Callable[[AntiWindup], list[SvgData]],
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
        color_map: dict[str, str],
) -> str:
    """Build and return the SVG for a controller block diagram.

    Args:
        build_controller_svg: Build controller diagram function.
        anti_windup: Selected anti-windup strategy.
        constraint: Tuple of (min, max) constraint values.
        color_map: Mapping of original SVG colors to new colors.

    Returns:
        A recolored SVG string representing the controller diagram.
    """
    svg_structure = build_controller_svg(anti_windup)
    merged_svg = merge_svg_layers(svg_structure)
    constrained_svg = inject_constraints_into_svg(merged_svg, constraint)
    recolored_svg = recolor_svg(constrained_svg, color_map)

    return recolored_svg


def load_closed_loop_diagram(
        build_controller_svg: Callable[[AntiWindup], list[SvgData]],
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
        color_map: dict[str, str] | None = None,
) -> str:
    """Build and return the SVG for a full closed-loop system diagram.

    Args:
        build_controller_svg: Build controller diagram function.
        anti_windup: Selected anti-windup strategy.
        constraint: Tuple of (min, max) constraint values.
        color_map: Optional Mapping of original SVG colors to new colors.

    Returns:
        A recolored SVG string representing the closed-loop diagram.
    """
    offset_x = 100
    offset_y = 0

    # Start with base closed-loop diagram
    svg_elements: list[SvgData] = [
        (BlockDiagram.closed_loop, (0, 0))
    ]

    controller_svgs = build_controller_svg(anti_windup)

    # Offset controller elements and append them
    for svg_name, (x, y) in controller_svgs:
        svg_elements.append((svg_name, (x + offset_x, y + offset_y)))

    merged_svg = merge_svg_layers(svg_elements)
    svg = inject_constraints_into_svg(merged_svg, constraint)
    if color_map is not None:
        svg = recolor_svg(svg, color_map)

    return svg


def merge_svg_layers(svg_data: list[SvgData]) -> str:
    """Merge multiple SVG files into a single SVG string.

    Args:
        svg_data: List of tuples containing SVG file names and their translations.

    Returns:
        A merged SVG string.
    """
    layers: list[SvgLayer] = []

    for filename, translation in svg_data:
        svg_path = BLOCK_DIAGRAM_DIR / filename

        # Read SVG content and wrap it as a layer with translation
        layers.append(
            SvgLayer(
                svg_path.read_text(encoding="utf-8"),
                translate=translation,
            )
        )

    return merge_svgs(layers)


def inject_constraints_into_svg(svg: str, constraint: tuple[float, float]) -> str:
    """Replace placeholder constraint values in the SVG.

    Args:
        svg: Input SVG string containing placeholders.
        constraint: Tuple of (min, max) constraint values.

    Returns:
        SVG string with injected constraint values.
    """
    min_val, max_val = constraint

    # Replace placeholder markers with actual values
    svg = svg.replace("min: ###", f"min: {min_val}")
    svg = svg.replace("max: ###", f"max: {max_val}")

    return svg


# ============================================================
# Controller Builder
# ============================================================
def _handle_anti_windup(anti_windup: AntiWindup, x: int, y: int) -> SvgData:
    match anti_windup:
        case AntiWindup.BACKCALCULATION:
            return BlockDiagram.backcalculation, (x, y)
        case AntiWindup.CLAMPING:
            return BlockDiagram.clamping, (x, y)
        case AntiWindup.CONDITIONAL:
            return BlockDiagram.conditional, (x, y)
        case unknown_value:
            raise ValueError(
                f"Unsupported anti-windup method: {unknown_value!r}. "
                "Expected one of: BACKCALCULATION, CLAMPING, CONDITIONAL."
            )


def get_pi_controller_svg(anti_windup: AntiWindup) -> list[SvgData]:
    """Define the structure (components + positions) of the controller diagram.

    Args:
        anti_windup: Selected anti-windup strategy.

    Returns:
        List of SVG elements with their positions.
    """
    # Layout offsets
    y_offset = 125
    node_x = 150
    sum_x = 475

    svg_elements: list[SvgData] = [
        (BlockDiagram.blank_base, (0, 0)),
        (BlockDiagram.controller_in, (0, y_offset)),
        (BlockDiagram.controller_out, (sum_x, y_offset)),
        (BlockDiagram.p_path, (node_x, y_offset)),
        _handle_anti_windup(anti_windup, node_x, y_offset),
    ]

    return svg_elements


def get_pid_controller_svg(anti_windup: AntiWindup) -> list[SvgData]:
    """Define the structure (components + positions) of the controller diagram.

    Args:
        anti_windup: Selected anti-windup strategy.

    Returns:
        List of SVG elements with their positions.
    """
    # Layout offsets
    y_offset = 125
    node_x = 150
    sum_x = 475

    svg_elements: list[SvgData] = [
        (BlockDiagram.blank_base, (0, 0)),
        (BlockDiagram.controller_in, (0, y_offset)),
        (BlockDiagram.controller_out, (sum_x, y_offset)),
        (BlockDiagram.p_path, (node_x, y_offset)),
        (BlockDiagram.d_path, (node_x, y_offset)),
        _handle_anti_windup(anti_windup, node_x, y_offset),
    ]

    return svg_elements

