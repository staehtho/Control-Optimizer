import re
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter, QIcon
from PySide6.QtCore import QByteArray, Qt



def recolor_svg(svg_text: str, color_map: dict[str, str]) -> str:
    for old, new in color_map.items():
        svg_text = svg_text.replace(old, new)
    return svg_text


def merge_svgs(svg_texts: list[str]) -> str:
    if not svg_texts:
        return ""

    root_attrs = _extract_svg_root_attrs(svg_texts[0])
    if "xmlns" not in root_attrs:
        root_attrs = f'{root_attrs} xmlns="http://www.w3.org/2000/svg"'.strip()

    merged_body = []
    for svg_text in svg_texts:
        inner = _extract_svg_inner(svg_text)
        if inner:
            merged_body.append(inner)

    return f"<svg {root_attrs}>\n" + "\n".join(merged_body) + "\n</svg>\n"


def _extract_svg_root_attrs(svg_text: str) -> str:
    match = re.search(r"<svg\b([^>]*)>", svg_text, flags=re.IGNORECASE)
    if match is None:
        return ""
    return match.group(1).strip()


def _extract_svg_inner(svg_text: str) -> str:
    match = re.search(r"<svg\b[^>]*>(.*)</svg>", svg_text, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return svg_text.strip()
    return match.group(1).strip()


def svg_to_icon(svg_text: str, size: int = 32) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)
