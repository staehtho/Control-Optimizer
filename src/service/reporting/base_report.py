from typing import Literal

from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from svglib.svglib import svg2rlg

from utils import latex_to_drawing

Alignment = Literal["LEFT", "CENTER", "RIGHT"]


def _convert_cell(cell):
    # Already a drawing
    if isinstance(cell, Drawing):
        return cell

    # LaTeX input
    if isinstance(cell, dict) and "latex" in cell:
        return latex_to_drawing(cell["latex"])

    return cell


class BaseReport:
    def __init__(self, filename: str, pagesize=A4, margin: int = 40) -> None:
        self.filename = filename
        self.pagesize = pagesize
        self.margin = margin

        self.styles = getSampleStyleSheet()
        self.story = []

        self.doc = SimpleDocTemplate(
            filename,
            pagesize=pagesize,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
        )

        self.header_text = "My Report Header"
        self.footer_text = "Page %d"

    # ============================================================
    # Header & Footer callbacks
    # ============================================================

    def _draw_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(self.margin, self.pagesize[1] - self.margin + 10, self.header_text)
        canvas.restoreState()

    def _draw_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        footer = self.footer_text % doc.page
        canvas.drawString(self.margin, self.margin - 20, footer)
        canvas.restoreState()

    def _on_page(self, canvas, doc):
        self._draw_header(canvas, doc)
        self._draw_footer(canvas, doc)

    # ============================================================
    # Generic helper methods
    # ============================================================

    def add_title(self, text: str) -> None:
        self.story.append(Paragraph(text, self.styles["Title"]))
        self.story.append(Spacer(1, 20))

    def add_heading(self, text: str) -> None:
        self.story.append(Paragraph(text, self.styles["Heading2"]))
        self.story.append(Spacer(1, 10))

    def add_paragraph(self, text: str) -> None:
        self.story.append(Paragraph(text, self.styles["BodyText"]))
        self.story.append(Spacer(1, 8))

    def add_table(self, header: list, data: list) -> None:
        # Convert all cells
        processed_header = [_convert_cell(c) for c in header]
        processed_data = [[_convert_cell(c) for c in row] for row in data]

        data_table = [processed_header] + processed_data

        table = Table(data_table)
        table.setStyle(TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),

            # Body
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),

            # Lines (minimalist!)
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),

            # Alignment
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            # Padding (huge visual impact)
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 15))

    def add_svg(
            self,
            svg_path: str,
            *,
            width: int | None = None,
            height: int | None = None,
            align: Alignment = "CENTER",
    ) -> None:
        drawing = svg2rlg(svg_path)

        if drawing is None:
            return

        original_width = drawing.width
        original_height = drawing.height

        # Determine scale factor
        if width is not None and height is not None:
            scale = min(width / original_width, height / original_height)
        elif width is not None:
            scale = width / original_width
        elif height is not None:
            scale = height / original_height
        else:
            scale = 1.0

        drawing.scale(scale, scale)

        # Properly update dimensions
        drawing.width *= scale
        drawing.height *= scale

        drawing.hAlign = align

        self.story.append(Spacer(1, 20))
        self.story.append(drawing)
        self.story.append(Spacer(1, 20))

    # ============================================================
    # Finalize PDF
    # ============================================================

    def build(self) -> None:
        self.doc.build(
            self.story,
            onFirstPage=self._on_page,
            onLaterPages=self._on_page,
        )
