from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from utils.svg_utils import recolor_svg
from app_domain.controlsys import AntiWindup

SVG_STYLE = """
<style>
    .fill { fill:#000000; }
    .line { stroke:#000000; stroke-width:2; fill:none; }
    .block { stroke:#000000; stroke-width:2; fill:none; }
    .text { fill:#000000; font-family:Arial, sans-serif; font-size:14px; text-anchor:middle; dominant-baseline:middle; }
</style>
"""
SUM_SVG = '<circle class="line" cx="0" cy="0" r="5"/>'
MINUS_SVG = '<line class="line" x1="-2.5" y1="0" x2="2.5" y2="0"/>'
ARROW_SVG = '<path class="fill" d="M0 0 L-5 2 L-5 -2" transform="scale(1.5)"/>'
NODE = '<circle class="fill" cx="0" cy="0" r="4"/>'

CONTROLLER_SVG_SIZE = (1300, 650)
CLOSED_LOOP_SVG_SIZE = (1850, 800)


@dataclass
class SvgData:
    translate: tuple[int, int]  # (x, y)
    rotate: int  # rotation in degrees
    inline_svg: Optional[str] = None  # dynamic SVG markup


type ControllerBuilder = Callable[[AntiWindup, tuple[float, float]], list[SvgData]]


# ============================================================
# Block diagram loader
# ============================================================

def load_controller_diagram(
        build_controller_svg: Callable[[AntiWindup, tuple[float, float]], list[SvgData]],
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
    svg = build_controller_svg(anti_windup, constraint)
    svg = create_svg(CONTROLLER_SVG_SIZE, svg)
    recolored_svg = recolor_svg(svg, color_map)

    return recolored_svg


def load_closed_loop_diagram(
        build_closed_loop_svg: Callable[[ControllerBuilder, AntiWindup, tuple[float, float]], list[SvgData]],
        build_controller_svg: ControllerBuilder,
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
    svg = build_closed_loop_svg(build_controller_svg, anti_windup, constraint)
    svg = create_svg(CLOSED_LOOP_SVG_SIZE, svg)

    if color_map is not None:
        svg = recolor_svg(svg, color_map)

    return svg


# ============================================================
# Closed loop builder
# ============================================================
def closed_loop_builder_svg(
        controller_builder_svg: ControllerBuilder,
        anti_windup: AntiWindup,
        constraint: tuple[float, float],
) -> list[SvgData]:
    elements = controller_builder_svg(anti_windup, constraint)

    # move the controller to the right
    for element in elements:
        element.translate = (element.translate[0] + 100, element.translate[1])

    elements.extend([
        build_path(0, 0, 85, "horizontal", label="r"),
        sum_configurator(95, 0, south="minus", west="plus"),
        param_block(725, 0, "G(s)", 50, 100),
        build_path(825, 0, 100, "horizontal", "end", "y"),
        node(875, 0),
        build_path(875, 0, 176, "vertical"),
        build_path(95, 10, 166, "vertical"),
        build_path(95, 175, 780, "horizontal"),
    ])

    return elements


# ============================================================
# Controller builder
# ============================================================
def anti_windup_section(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:

    match anti_windup:
        case AntiWindup.CLAMPING:
            return [
                build_path(250, 75, 75, "horizontal", "end"),
                integrator(325, 75, constraints),
                build_path(375, 75, 100, "horizontal"),
                build_path(475, 76, -65, "vertical"),
            ]
        case AntiWindup.CONDITIONAL:
            return [
                build_path(250, 75, 15, "horizontal"),
                build_path(265, 76, -17, "vertical"),
                build_path(265, 60, 60, "horizontal", "end"),
                decider(325, 75),
                build_path(375, 75, 25, "horizontal", "end"),
                integrator(400, 75),
                build_path(450, 75, 25, "horizontal"),
                build_path(475, 76, -65, "vertical"),
                node(500, 0),
                node(600, 0),
                sum_configurator(500, 125, north="minus", east="plus"),
                build_path(500, 0, 120, "vertical"),
                build_path(600, 0, 125, "vertical"),
                build_path(510, 125, 91, "horizontal"),
                build_path(495, 125, -220, "horizontal"),
                build_path(275, 126, -50, "vertical"),
                build_path(274, 75, 50, "horizontal", "end"),
                build_path(305, 90, 20, "horizontal", "end"),
                text(296, 95, "0", 14)
            ]
        case AntiWindup.BACKCALCULATION:
            return [
                build_path(250, 75, 30, "horizontal"),
                sum_configurator(290, 75, south="plus", west="plus"),
                build_path(295, 75, 30, "horizontal", "end"),
                integrator(325, 75),
                build_path(375, 75, 100, "horizontal"),
                build_path(475, 76, -65, "vertical"),
                node(500, 0),
                node(600, 0),
                sum_configurator(500, 125, north="minus", east="plus"),
                build_path(500, 0, 120, "vertical"),
                build_path(600, 0, 125, "vertical"),
                build_path(510, 125, 91, "horizontal"),
                build_path(450, 125, 45, "horizontal", "start"),
                param_block(400, 125, "Ka"),
                build_path(290, 85, 41, "vertical"),
                build_path(290, 125, 110, "horizontal"),
            ]


def get_pi_controller_svg(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:
    elements = [
        build_path(0, 0, 50, "horizontal", "end", "e"),
        param_block(50, 0, "Kp"),
        build_path(100, 0, 365, "horizontal"),
        sum_configurator(475, 0, west="plus", south="plus"),
        node(150, 0),
        build_path(480, 0, 45, "horizontal", "end"),
        saturation(525, 0, constraints),
        build_path(575, 0, 50, "horizontal", "end", "u"),
        build_path(150, 0, 76, "vertical"),
        build_path(150, 75, 50, "horizontal", "end"),
        param_block_as_fraction(200, 75, "Ti"),
    ]

    elements.extend(anti_windup_section(anti_windup, constraints))

    return elements


def get_pid_controller_svg(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:
    elements = [
        build_path(0, 0, 50, "horizontal", "end", "e"),
        param_block(50, 0, "Kp"),
        build_path(100, 0, 365, "horizontal"),
        sum_configurator(475, 0, north="plus", west="plus", south="plus"),
        node(150, 0),
        build_path(150, 0, -76, "vertical"),
        build_path(150, -75, 50, "horizontal", "end"),
        param_block(200, -75, "Td"),
        build_path(250, -75, 50, "horizontal", "end"),
        filter_with_differentiator(300, -75),
        build_path(400, -75, 75, "horizontal"),
        build_path(475, -76, 65, "vertical"),
        build_path(480, 0, 45, "horizontal", "end"),
        saturation(525, 0, constraints),
        build_path(575, 0, 50, "horizontal", "end", "u"),
        build_path(150, 0, 76, "vertical"),
        build_path(150, 75, 50, "horizontal", "end"),
        param_block_as_fraction(200, 75, "Ti"),
    ]

    elements.extend(anti_windup_section(anti_windup, constraints))

    return elements


# ============================================================
# SVG elements
# ============================================================
def create_svg(size: tuple[int, int], elements: list[SvgData]) -> str:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 -{size[1] / 4} {size[0] / 2} {size[1] / 2}">'
    svg += SVG_STYLE
    for element in elements:
        svg += f'<g transform="translate({element.translate[0]},{element.translate[1]}) rotate({element.rotate})">{element.inline_svg}</g>'

    svg += '</svg>'
    return svg


def sum_configurator(
        x: int,
        y: int,
        north: str = "",
        east: str = "",
        south: str = "",
        west: str = ""
) -> SvgData:
    parts: list[str] = []

    # NORTH
    if north != "":
        parts.append(f'<g transform="translate(0,-5) rotate(90)">{ARROW_SVG}</g>')
        if north == "minus":
            parts.append(f'<g transform="translate(8,-15)">{MINUS_SVG}</g>')

    # EAST
    if east != "":
        parts.append(f'<g transform="translate(5,0) rotate(180)">{ARROW_SVG}</g>')
        if east == "minus":
            parts.append(f'<g transform="translate(15,8) rotate(90)">{MINUS_SVG}</g>')

    # SOUTH
    if south != "":
        parts.append(f'<g transform="translate(0,5) rotate(-90)">{ARROW_SVG}</g>')
        if south == "minus":
            parts.append(f'<g transform="translate(-8,15)">{MINUS_SVG}</g>')

    # WEST
    if west != "":
        parts.append(f'<g transform="translate(-5,0)">{ARROW_SVG}</g>')
        if west == "minus":
            parts.append(f'<g transform="translate(-15,-8) rotate(90)">{MINUS_SVG}</g>')

    # CENTER SUM CIRCLE
    parts.append(f'<g transform="translate(0,0)">{SUM_SVG}</g>')

    # Wrap everything in ONE group
    grouped_svg = f"<g>{''.join(parts)}</g>"

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=grouped_svg
    )


def build_path(
        x: int,
        y: int,
        length: int,
        orientation: str = "horizontal",  # "horizontal" | "vertical"
        arrow_pos: str = "none",  # "start" | "end" | "none"
        label: str = ""
) -> SvgData:
    # Arrow rotation logic
    if orientation == "horizontal":
        arrow_rotation = 0
        label_x = length / 2
        label_y = -15
        label_anchor = "middle"  # FIX
    else:  # vertical
        arrow_rotation = 90
        label_x = -15
        label_y = length / 2
        label_anchor = "end"  # FIX

    label_svg = ""
    if label != "":
        label_svg = (
            f'<text class ="text" style="text-anchor:{label_anchor}" '
            f'x="{label_x}" y="{label_y}">{label}</text>'
        )

    # Arrow placement
    arrow_svg = ""
    if arrow_pos == "start":
        line = f'<line x1="5" y1="0" x2="{length}" y2="0" stroke="#000000" stroke-width="2"/>'
        arrow_svg = f'<g transform="rotate(180)">{ARROW_SVG}</g>'

    elif arrow_pos == "end":
        line = f'<line x1="0" y1="0" x2="{length - 5}" y2="0" stroke="#000000" stroke-width="2"/>'
        arrow_svg = f'<g transform="translate({length},0)">{ARROW_SVG}</g>'

    else:
        line = f'<line x1="0" y1="0" x2="{length}" y2="0" stroke="#000000" stroke-width="2"/>'

    grouped_line = f'<g transform="rotate({arrow_rotation})">{line}{arrow_svg}</g>'

    # Group everything
    grouped = f'<g>{grouped_line}{label_svg}</g>'

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=grouped
    )


def node(x: int, y: int) -> SvgData:
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=NODE
    )


def param_block(x: int, y: int, param: str, height: int = 50, width: int = 50) -> SvgData:
    block = f"""
    <g transform="translate(0, -{height / 2})">'
        '<rect class="block" height="{height}" width="{width}"/>'
        '<text class="text" x="{width / 2}" y="{height / 5 * 3}">{param}</text>'
    '</g>
    """

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=block
    )


def param_block_as_fraction(x: int, y: int, param: str) -> SvgData:
    block = f"""
    <g transform="translate(0, -25)">
        '<rect class="block" height="50" width="50"/>'
        <text class="text" x="25" y="17.5">1</text>
        <path class="line" d="M17.5 25 H32.5"/>
        <text class="text" x="25" y="40">{param}</text>
    </g>
    """

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=block
    )


def saturation(x: int, y: int, constraint: tuple[float, float]) -> SvgData:
    sat = f"""
    <g transform="translate(0, -25)">
        <rect class="block" height="50" width="50"/>
        <path class="line" d="M7 40 H20 L30 10 H43"/>
        <path class="line" d="M5 25 H45" style="stroke-width:0.7"/>
        <path class="line" d="M25 5 V45" style="stroke-width:0.7"/>
        <!-- min max -->
        <text class="text" x="0" y="-8" style="font-size:10px; text-anchor:start">max: {constraint[1]}</text>
        <text class="text" x="0" y="65" style="font-size:10px; text-anchor:start">min: {constraint[0]}</text>
    </g>
    """
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=sat
    )


def filter_with_differentiator(x: int, y: int) -> SvgData:
    tf = f"""
    <g transform="translate(0, -25)">
        <rect class="block" height="50" width="100"/>
        <!-- num -->
        <text class="text" x="50" y="17.5">s</text>
        <path class="line" d="M17.5 25 H82.5"/>
        <!-- den -->
        <text class="text" x="50" y="40">Tf s + 1</text>
    </g>
    """
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=tf
    )


def integrator(x: int, y: int, constraint: Optional[tuple[float, float]] = None) -> SvgData:
    if constraint is None:
        tf = f"""
        <g transform="translate(0, -25)">
            '<rect class="block" height="50" width="50"/>'
            <text class="text" x="25" y="17.5">1</text>
            <path class="line" d="M17.5 25 H32.5"/>
            <text class="text" x="25" y="40">s</text>
        </g>
        """
    else:
        tf = f"""
        <g transform="translate(0, -25)">
            <rect class="block" height="50" width="50"/>
            <text class="text" x="15" y="17.5">1</text>
            <path class="line" d="M7.5 25 H22.5"/>
            <text class="text" x="15" y="40">s</text>

            <!-- clamping -->
            <path class="line" d="M25 40 H32.5 L37.5 10 H45"/>

            <!-- min max -->
            <text class="text" x="0" y="-8" style="font-size:10px; text-anchor:start">max: {constraint[1]}</text>
            <text class="text" x="0" y="65" style="font-size:10px; text-anchor:start">min: {constraint[0]}</text>
        </g>"""

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=tf
    )


def decider(x: int, y: int) -> SvgData:
    dec = """
    <g transform="translate(0, -25)">
        <rect class="block" height="50" width="50"/>

        <path class="line" d="M0 10 H10 L40 25 H50"/>
        <path class="line" d="M0 40 H10"/>
        <path class="line" d="M0 25 H5"/>
        <text class="text" x="12.5" y="28" style="font-size:10px">>0</text>

        <circle class="line" cx="10" cy="10" r="1.25" style="stroke-width:3"/>
        <circle class="line" cx="40" cy="25" r="1.25" style="stroke-width:3"/>
        <circle class="line" cx="10" cy="40" r="1.25" style="stroke-width:3"/>
    </g>
    """
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=dec
    )


def text(x: int, y: int, label: str, font_size: int = 10) -> SvgData:
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=f'<text class="text" x="0" y="0" style="font-size:{font_size}px; text-anchor:start">{label}</text>'
    )
