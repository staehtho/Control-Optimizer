from __future__ import annotations

from typing import Callable

from app_domain.controlsys import AntiWindup
from .svg_primitives import (
    SvgData,
    build_path,
    node,
    param_block,
    param_block_as_fraction,
    saturation,
    filter_with_differentiator,
    integrator,
    decider,
    sum_configurator,
    text,
)

type ControllerBuilder = Callable[[AntiWindup, tuple[float, float]], list[SvgData]]


def anti_windup_section(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:
    """Build the anti-windup sub-diagram for the selected strategy."""
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
                node(525, 0),
                node(625, 0),
                sum_configurator(525, 125, north="minus", east="plus"),
                build_path(525, 0, 120, "vertical"),
                build_path(625, 0, 125, "vertical"),
                build_path(535, 125, 91, "horizontal"),
                build_path(275, 125, 245, "horizontal"),
                build_path(275, 126, -50, "vertical"),
                build_path(274, 75, 50, "horizontal", "end"),
                build_path(305, 90, 20, "horizontal", "end"),
                text(296, 95, "0", 14),
            ]
        case AntiWindup.BACKCALCULATION:
            return [
                build_path(250, 75, 30, "horizontal"),
                sum_configurator(290, 75, south="plus", west="plus"),
                build_path(295, 75, 30, "horizontal", "end"),
                integrator(325, 75),
                build_path(375, 75, 100, "horizontal"),
                build_path(475, 76, -65, "vertical"),
                node(525, 0),
                node(625, 0),
                sum_configurator(525, 125, north="minus", east="plus"),
                build_path(525, 0, 120, "vertical"),
                build_path(625, 0, 125, "vertical"),
                build_path(535, 125, 91, "horizontal"),
                build_path(450, 125, 70, "horizontal", "start"),
                param_block(400, 125, "Ka"),
                build_path(290, 85, 41, "vertical"),
                build_path(290, 125, 110, "horizontal"),
            ]


def get_pi_controller_svg(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:
    """Build the SVG elements for a PI controller block diagram."""
    elements = [
        build_path(0, 0, 50, "horizontal", "end", "e"),
        param_block(50, 0, "Kp"),
        build_path(100, 0, 365, "horizontal"),
        sum_configurator(475, 0, west="plus", south="plus"),
        node(150, 0),
        build_path(480, 0, 70, "horizontal", "end"),
        saturation(550, 0, constraints),
        build_path(600, 0, 50, "horizontal", "end", "u"),
        build_path(150, 0, 76, "vertical"),
        build_path(150, 75, 50, "horizontal", "end"),
        param_block_as_fraction(200, 75, "Ti"),
    ]

    elements.extend(anti_windup_section(anti_windup, constraints))

    return elements


def get_pid_controller_svg(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:
    """Build the SVG elements for a PID controller block diagram."""
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
        build_path(480, 0, 70, "horizontal", "end"),
        saturation(550, 0, constraints),
        build_path(600, 0, 50, "horizontal", "end", "u"),
        build_path(150, 0, 76, "vertical"),
        build_path(150, 75, 50, "horizontal", "end"),
        param_block_as_fraction(200, 75, "Ti"),
    ]

    elements.extend(anti_windup_section(anti_windup, constraints))

    return elements


def get_ff_pid_controller_svg(anti_windup: AntiWindup, constraints: tuple[float, float]) -> list[SvgData]:
    """Build the SVG elements for a PID controller block diagram."""
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
        build_path(480, 0, 15, "horizontal"),
        sum_configurator(505, 0, west="plus", north="plus"),
        build_path(510, 0, 40, "horizontal", "end"),
        saturation(550, 0, constraints),
        build_path(600, 0, 50, "horizontal", "end", "u"),
        build_path(150, 0, 76, "vertical"),
        build_path(150, 75, 50, "horizontal", "end"),
        param_block_as_fraction(200, 75, "Ti"),

        # Feed-forward branch
        param_block(50, -125, "Kff"),
        build_path(100, -125, 405, "horizontal"),
        build_path(505, -126, 120, "vertical"),
        build_path(0, -125, 50, "horizontal", "end", "r", tag="kff_r"),
    ]

    elements.extend(anti_windup_section(anti_windup, constraints))

    return elements
