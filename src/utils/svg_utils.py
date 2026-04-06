import io
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter, QIcon
from PySide6.QtCore import QByteArray, Qt
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure


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
    svg_text = _inline_svg_class_styles(svg_text)
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


def _inline_svg_class_styles(svg_text: str) -> str:
    class_styles = _extract_simple_class_styles(svg_text)

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        class_match = re.search(r'\bclass\s*=\s*"([^"]+)"', tag, flags=re.IGNORECASE)
        if class_match is None:
            return tag

        classes = [cls for cls in class_match.group(1).split() if cls]
        styles = [class_styles[cls] for cls in classes if cls in class_styles]

        tag = re.sub(r'\s*\bclass\s*=\s*"[^"]*"', "", tag, count=1, flags=re.IGNORECASE)
        if not styles:
            return tag

        style_match = re.search(r'\bstyle\s*=\s*"([^"]*)"', tag, flags=re.IGNORECASE)
        class_style = "; ".join(style.rstrip(" ;") for style in styles if style.strip())
        if style_match is not None:
            existing_style = style_match.group(1).strip()
            merged_style = _merge_style_declarations(class_style, existing_style)
            return re.sub(
                r'\bstyle\s*=\s*"[^"]*"',
                f'style="{merged_style}"',
                tag,
                count=1,
                flags=re.IGNORECASE,
            )

        closing = "/>" if tag.endswith("/>") else ">"
        return tag[:-len(closing)] + f' style="{class_style}"{closing}'

    svg_text = re.sub(r"<([a-zA-Z][^/\s>]*)\b[^>]*class\s*=\s*\"[^\"]+\"[^>]*/?>", repl, svg_text)
    return re.sub(r"<style\b[^>]*>.*?</style>", "", svg_text, flags=re.IGNORECASE | re.DOTALL)


def _extract_simple_class_styles(svg_text: str) -> dict[str, str]:
    class_styles: dict[str, str] = {}

    for style_match in re.finditer(r"<style\b[^>]*>(.*?)</style>", svg_text, flags=re.IGNORECASE | re.DOTALL):
        css = style_match.group(1)
        for rule_match in re.finditer(r"\.([a-zA-Z_][\w\-]*)\s*\{([^{}]+)\}", css):
            class_name = rule_match.group(1)
            declarations = rule_match.group(2).strip().rstrip(" ;")
            if declarations:
                class_styles[class_name] = declarations

    return class_styles


def _merge_style_declarations(base_style: str, override_style: str) -> str:
    merged: list[tuple[str | None, str]] = []
    index_by_name: dict[str, int] = {}

    for declaration in _parse_style_declarations(base_style):
        name = declaration[0]
        if name is not None:
            index_by_name[name] = len(merged)
        merged.append(declaration)

    for declaration in _parse_style_declarations(override_style):
        name = declaration[0]
        if name is not None and name in index_by_name:
            merged[index_by_name[name]] = declaration
        else:
            if name is not None:
                index_by_name[name] = len(merged)
            merged.append(declaration)

    return "; ".join(value for _, value in merged if value).strip()


def _parse_style_declarations(style_text: str) -> list[tuple[str | None, str]]:
    declarations: list[tuple[str | None, str]] = []

    for raw_declaration in style_text.split(";"):
        declaration = raw_declaration.strip()
        if not declaration:
            continue

        if ":" not in declaration:
            declarations.append((None, declaration))
            continue

        name, value = declaration.split(":", 1)
        normalized_name = name.strip().lower()
        normalized_value = value.strip()
        declarations.append((normalized_name, f"{normalized_name}:{normalized_value}"))

    return declarations


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
    path: Path = Path(path)

    # Optional: inject width/height if missing
    if 'width=' not in svg_content and 'height=' not in svg_content:
        svg_content = svg_content.replace(
            "<svg",
            f'<svg width="{size}" height="{size}"',
            1
        )

    path.write_text(svg_content, encoding="utf-8")


def latex_to_svg(text: str, font_size: float | None = None) -> str:
    logical_dpi = 96.0

    # --- Figure (off-screen SVG canvas) ---
    fig = Figure(figsize=(0.01, 0.01))
    canvas = (FigureCanvasSVG(fig))
    fig.patch.set_alpha(0)

    text_kwargs = {
        "ha": "left",
        "va": "bottom",
    }
    if font_size is not None:
        text_kwargs["fontsize"] = str(font_size)

    fig.text(
        0,
        0,
        f"${text}$",
        **text_kwargs,
    )

    # --- Render ---
    buf = io.StringIO()
    fig.savefig(
        buf,
        format="svg",
        dpi=logical_dpi,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True,
    )
    canvas.draw()

    svg_text = buf.getvalue()

    return svg_text
