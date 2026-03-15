"""Icon loading helpers for Qt views."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

from utils import recolor_svg, svg_to_icon
from views.resources import ICONS_DIR


# ============================================================
# Icon Utilities
# ============================================================

def load_icon(color_map: dict[str, str], svg_path: str | Path, size: int = 24) -> QIcon:
    """Load an SVG icon and recolor it using the current theme."""
    svg_path = ICONS_DIR / svg_path
    svg_text = svg_path.read_text(encoding="utf-8")
    recolored = recolor_svg(svg_text, color_map)
    return svg_to_icon(recolored, size)
