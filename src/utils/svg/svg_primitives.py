from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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


@dataclass
class SvgData:
    translate: tuple[int, int]
    rotate: int
    inline_svg: Optional[str] = None


def sum_configurator(
        x: int,
        y: int,
        north: str = "",
        east: str = "",
        south: str = "",
        west: str = "",
) -> SvgData:
    """Create a configurable summing junction with directional signs."""
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
        inline_svg=grouped_svg,
    )


def build_path(
        x: int,
        y: int,
        length: int,
        orientation: str = "horizontal",  # "horizontal" | "vertical"
        arrow_pos: str = "none",  # "start" | "end" | "none"
        label: str = "",
) -> SvgData:
    """Create a straight signal line with optional arrow and label."""
    # Arrow rotation logic
    if orientation == "horizontal":
        arrow_rotation = 0
        label_x = length / 2
        label_y = -15
        label_anchor = "middle"
    else:  # vertical
        arrow_rotation = 90
        label_x = -15
        label_y = length / 2
        label_anchor = "end"

    label_svg = ""
    if label != "":
        label_svg = (
            f'<text class="text" style="text-anchor:{label_anchor}" '
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
    grouped = f"<g>{grouped_line}{label_svg}</g>"

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=grouped,
    )


def node(x: int, y: int) -> SvgData:
    """Create a filled node (connection dot)."""
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=NODE,
    )


def param_block(x: int, y: int, param: str, height: int = 50, width: int = 50) -> SvgData:
    """Create a rectangular parameter block with a label."""
    block = f"""
    <g transform="translate(0, -{height / 2})">
        <rect class="block" height="{height}" width="{width}"/>
        <text class="text" x="{width / 2}" y="{height / 5 * 3}">{param}</text>
    </g>
    """

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=block,
    )


def param_block_as_fraction(x: int, y: int, param: str) -> SvgData:
    """Create a parameter block representing a reciprocal (1 / param)."""
    block = """
    <g transform="translate(0, -25)">
        <rect class="block" height="50" width="50"/>
        <text class="text" x="25" y="17.5">1</text>
        <path class="line" d="M17.5 25 H32.5"/>
        <text class="text" x="25" y="40">{param}</text>
    </g>
    """.format(param=param)

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=block,
    )


def saturation(x: int, y: int, constraint: tuple[float, float]) -> SvgData:
    """Create a saturation block with min/max annotations."""
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
        inline_svg=sat,
    )


def filter_with_differentiator(x: int, y: int) -> SvgData:
    """Create a differentiator block with first-order filter (Tf s + 1)."""
    tf = """
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
        inline_svg=tf,
    )


def integrator(x: int, y: int, constraint: Optional[tuple[float, float]] = None) -> SvgData:
    """Create an integrator block, optionally with clamping visualization."""
    if constraint is None:
        tf = """
        <g transform="translate(0, -25)">
            <rect class="block" height="50" width="50"/>
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
        </g>
        """

    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=tf,
    )


def decider(x: int, y: int) -> SvgData:
    """Create a conditional-integration decision block."""
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
        inline_svg=dec,
    )


def text(x: int, y: int, label: str, font_size: int = 10) -> SvgData:
    """Create a positioned text label."""
    return SvgData(
        translate=(x, y),
        rotate=0,
        inline_svg=(
            f'<text class="text" x="0" y="0" '
            f'style="font-size:{font_size}px; text-anchor:start">{label}</text>'
        ),
    )
