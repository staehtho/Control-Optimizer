from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from numpy import ndarray
from dataclasses import dataclass

if TYPE_CHECKING:
    from app_domain.controlsys import MySolver


@dataclass
class PlantResponseContext:
    """Context for plant response computation."""

    num: list[float]
    den: list[float]

    t0: float
    t1: float

    solver: MySolver

    reference: Callable[[ndarray], ndarray]
