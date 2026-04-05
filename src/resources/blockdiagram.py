from __future__ import annotations

from .resources import BlockDiagram, BLOCK_DIAGRAM_DIR
from utils.svg_utils import SvgLayer, merge_svgs, recolor_svg
from app_domain.controlsys import AntiWindup

type SvgData = tuple[str, tuple[int, int]]


def load_controller_diagram(
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
        color_map: dict[str, str],
) -> str:
    """Build and return the SVG for a controller block diagram.

    Args:
        anti_windup: Selected anti-windup strategy.
        constraint: Tuple of (min, max) constraint values.
        color_map: Mapping of original SVG colors to new colors.

    Returns:
        A recolored SVG string representing the controller diagram.
    """
    svg_structure = build_controller_svg_structure(anti_windup)
    merged_svg = merge_svg_layers(svg_structure)
    constrained_svg = inject_constraints_into_svg(merged_svg, constraint)
    recolored_svg = recolor_svg(constrained_svg, color_map)

    return recolored_svg


def load_closed_loop_diagram(
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
        color_map: dict[str, str],
) -> str:
    """Build and return the SVG for a full closed-loop system diagram.

    Args:
        anti_windup: Selected anti-windup strategy.
        constraint: Tuple of (min, max) constraint values.
        color_map: Mapping of original SVG colors to new colors.

    Returns:
        A recolored SVG string representing the closed-loop diagram.
    """
    offset_x = 100
    offset_y = 0

    # Start with base closed-loop diagram
    svg_elements: list[SvgData] = [
        (BlockDiagram.closed_loop, (0, 0))
    ]

    controller_svgs = build_controller_svg_structure(anti_windup)

    # Offset controller elements and append them
    for svg_name, (x, y) in controller_svgs:
        svg_elements.append((svg_name, (x + offset_x, y + offset_y)))

    merged_svg = merge_svg_layers(svg_elements)
    constrained_svg = inject_constraints_into_svg(merged_svg, constraint)
    recolored_svg = recolor_svg(constrained_svg, color_map)

    return recolored_svg


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


def build_controller_svg_structure(anti_windup: AntiWindup) -> list[SvgData]:
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
    ]

    # Add anti-windup block depending on selected strategy
    match anti_windup:
        case AntiWindup.BACKCALCULATION:
            svg_elements.append((BlockDiagram.backcalculation, (node_x, y_offset)))
        case AntiWindup.CLAMPING:
            svg_elements.append((BlockDiagram.clamping, (node_x, y_offset)))
        case AntiWindup.CONDITIONAL:
            svg_elements.append((BlockDiagram.conditional, (node_x, y_offset)))
        case unknown_value:
            raise ValueError(
                f"Unsupported anti-windup method: {unknown_value!r}. "
                "Expected one of: BACKCALCULATION, CLAMPING, CONDITIONAL."
            )

    return svg_elements


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
