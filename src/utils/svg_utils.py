import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter, QIcon
from PySide6.QtCore import QByteArray, Qt


@dataclass
class SvgLayer:
    svg: str
    translate: tuple[float, float] = (0, 0)


def recolor_svg(svg_text: str, color_map: dict[str, str]) -> str:
    for old, new in color_map.items():
        svg_text = svg_text.replace(old, new)
    return svg_text


def merge_svgs(layers: list[SvgLayer]) -> str:
    if not layers:
        return ""

    root_attrs = _extract_svg_root_attrs(layers[0].svg)
    if "xmlns" not in root_attrs:
        root_attrs = f'{root_attrs} xmlns="http://www.w3.org/2000/svg"'.strip()

    merged_body: list[str] = []

    for idx, layer in enumerate(layers):
        scoped_group_id = f"merged_svg_{idx}"
        defs_suffix = f"__m{idx}"

        prepared = _prepare_svg_for_merge(layer.svg, scoped_group_id, defs_suffix)
        inner = _extract_svg_inner(prepared)

        tx, ty = layer.translate
        transform_attr = ""
        if tx or ty:
            transform_attr = f' transform="translate({tx},{ty})"'

        if inner:
            merged_body.append(
                f'<g id="{scoped_group_id}"{transform_attr}>\n{inner}\n</g>'
            )

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


def _prepare_svg_for_merge(svg_text: str, scope_id: str, defs_suffix: str) -> str:
    svg_text = _suffix_defs_ids(svg_text, defs_suffix)
    svg_text = _scope_svg_styles(svg_text, f"#{scope_id}")
    return svg_text


def _suffix_defs_ids(svg_text: str, suffix: str) -> str:
    defs_blocks = re.findall(r"<defs\b[^>]*>.*?</defs>", svg_text, flags=re.IGNORECASE | re.DOTALL)
    if not defs_blocks:
        return svg_text

    id_map: dict[str, str] = {}
    for block in defs_blocks:
        for match in re.finditer(r'\bid="([^"]+)"', block):
            old_id = match.group(1)
            if old_id not in id_map:
                id_map[old_id] = f"{old_id}{suffix}"

    if not id_map:
        return svg_text

    def repl_defs(match: re.Match) -> str:
        block = match.group(0)
        for old_id, new_id in id_map.items():
            block = re.sub(rf'\bid="{re.escape(old_id)}"', f'id="{new_id}"', block)
        return block

    svg_text = re.sub(r"<defs\b[^>]*>.*?</defs>", repl_defs, svg_text, flags=re.IGNORECASE | re.DOTALL)
    svg_text = _replace_id_references(svg_text, id_map)
    return svg_text


def _replace_id_references(svg_text: str, id_map: dict[str, str]) -> str:
    for old_id, new_id in id_map.items():
        svg_text = re.sub(rf"url\(\s*#{re.escape(old_id)}\s*\)", f"url(#{new_id})", svg_text)
        svg_text = re.sub(
            rf'(\b(?:xlink:)?href\s*=\s*")#{re.escape(old_id)}(")',
            rf"\1#{new_id}\2",
            svg_text,
            flags=re.IGNORECASE,
        )
    return svg_text


def _scope_svg_styles(svg_text: str, scope: str) -> str:
    def repl(match: re.Match) -> str:
        css = match.group(1)
        scoped_css = _scope_css_selectors(css, scope)
        return f"<style>{scoped_css}</style>"

    return re.sub(r"<style\b[^>]*>(.*?)</style>", repl, svg_text, flags=re.IGNORECASE | re.DOTALL)


def _scope_css_selectors(css_text: str, scope: str) -> str:
    i = 0
    n = len(css_text)
    out: list[str] = []

    while i < n:
        start = css_text.find("{", i)
        if start == -1:
            out.append(css_text[i:])
            break
        selector = css_text[i:start].strip()
        end = css_text.find("}", start + 1)
        if end == -1:
            out.append(css_text[i:])
            break

        body = css_text[start + 1:end]

        if selector:
            if selector.startswith("@"):
                out.append(f"{selector}{{{body}}}")
            else:
                selectors = [s.strip() for s in selector.split(",") if s.strip()]
                scoped_selector = ", ".join(f"{scope} {s}" for s in selectors)
                out.append(f"{scoped_selector}{{{body}}}")
        else:
            out.append(f"{{{body}}}")

        i = end + 1

    return "".join(out)


def svg_to_icon(svg_text: str, size: int = 32) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


def save_svg(path: str | Path, svg_content: str, size: int = 32) -> None:
    path = Path(path)

    # Optional: inject width/height if missing
    if 'width=' not in svg_content and 'height=' not in svg_content:
        svg_content = svg_content.replace(
            "<svg",
            f'<svg width="{size}" height="{size}"',
            1
        )

    path.write_text(svg_content, encoding="utf-8")
