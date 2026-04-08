from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from svglib.svglib import svg2rlg

from utils import latex_to_drawing

ACCENT = colors.HexColor("#2A6FDB")
ACCENT_LIGHT = colors.HexColor("#E8F0FF")
TEXT_DARK = colors.HexColor("#222222")


def _convert_cell(cell):
    # Already a drawing
    if isinstance(cell, Drawing):
        return cell

    # LaTeX input
    if isinstance(cell, dict) and "latex" in cell:
        return latex_to_drawing(cell["latex"])

    return cell


class BaseReport:
    def __init__(self, filename: str, pagesize=A4, margin: int = 50) -> None:
        self.filename = filename
        self.pagesize = pagesize
        self.margin = margin

        # Load default styles
        self.styles = getSampleStyleSheet()

        # Add modern custom styles (unique names!)
        self.styles.add(ParagraphStyle(
            name="ModernHeading2",
            parent=self.styles["Heading2"],
            textColor=ACCENT,
            spaceAfter=12,
        ))

        self.styles.add(ParagraphStyle(
            name="ModernHeading3",
            parent=self.styles["Heading3"],
            textColor=TEXT_DARK,
            spaceAfter=8,
        ))

        self.styles.add(ParagraphStyle(
            name="ModernBody",
            parent=self.styles["BodyText"],
            fontSize=10.5,
            leading=14,
            textColor=TEXT_DARK,
        ))

        self.styles.add(ParagraphStyle(
            name="ModernTitle",
            parent=self.styles["Title"],
            textColor=ACCENT,
            fontSize=22,
            leading=26,
            spaceAfter=20,
        ))

        self.story = []

        self.doc = SimpleDocTemplate(
            filename,
            pagesize=pagesize,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin + 20,
            bottomMargin=margin + 20,
        )

        self.header_text = "Control Optimizer Report"
        self.footer_text = "Page %d"

    # ============================================================
    # Header & Footer
    # ============================================================

    def _draw_header(self, canvas, doc):
        canvas.saveState()

        canvas.setFillColor(ACCENT)
        canvas.rect(
            0,
            self.pagesize[1] - self.margin + 5,
            self.pagesize[0],
            25,
            fill=True,
            stroke=False,
        )

        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.white)
        canvas.drawString(
            self.margin,
            self.pagesize[1] - self.margin + 12,
            self.header_text,
        )

        canvas.restoreState()

    def _draw_footer(self, canvas, doc):
        canvas.saveState()

        canvas.setFillColor(ACCENT_LIGHT)
        canvas.rect(
            0,
            0,
            self.pagesize[0],
            25,
            fill=True,
            stroke=False,
        )

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(TEXT_DARK)
        footer = self.footer_text % doc.page
        canvas.drawString(self.margin, 10, footer)

        canvas.restoreState()

    def _on_page(self, canvas, doc):
        self._draw_header(canvas, doc)
        self._draw_footer(canvas, doc)

    # ============================================================
    # Content helpers
    # ============================================================

    def add_title(self, text: str) -> None:
        self.story.append(Paragraph(text, self.styles["ModernTitle"]))
        self.story.append(Spacer(1, 20))

    def add_heading(self, text: str) -> None:
        self.story.append(Paragraph(text, self.styles["ModernHeading2"]))
        self.story.append(Spacer(1, 6))

    def add_subheading(self, text: str) -> None:
        self.story.append(Paragraph(text, self.styles["ModernHeading3"]))
        self.story.append(Spacer(1, 4))

    def add_paragraph(self, text: str) -> None:
        """Use original BodyText for LaTeX compatibility."""
        self.story.append(Paragraph(text, self.styles["BodyText"]))
        self.story.append(Spacer(1, 6))

    def add_modern_paragraph(self, text: str) -> None:
        """Use modern style for plain text only."""
        self.story.append(Paragraph(text, self.styles["ModernBody"]))
        self.story.append(Spacer(1, 6))

    def add_itemize(self, items: list[str]) -> None:
        list_items = [
            ListItem(Paragraph(item, self.styles["ModernBody"]), leftIndent=12)
            for item in items
        ]
        bullet_list = ListFlowable(
            list_items,
            bulletType="bullet",
            leftIndent=12,
        )
        self.story.append(bullet_list)
        self.story.append(Spacer(1, 8))

    def add_table(self, header: list, data: list, width: int = 300) -> None:
        # Convert all cells (IMPORTANT for LaTeX!)
        processed_header = [_convert_cell(c) for c in header]
        processed_data = [[_convert_cell(c) for c in row] for row in data]

        table_data = [processed_header] + processed_data
        n_cols = len(header)
        col_widths = [width / n_cols] * n_cols

        table = Table(table_data, colWidths=col_widths)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT_LIGHT),
            ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_DARK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),

            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9.5),

            ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT),

            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        self.story.append(table)
        self.story.append(Spacer(1, 15))

    def add_svg(self, svg_path: str, *, width=None, height=None, align="CENTER"):
        drawing = svg2rlg(svg_path)
        if drawing is None:
            return

        original_width = drawing.width
        original_height = drawing.height

        if width and height:
            scale = min(width / original_width, height / original_height)
        elif width:
            scale = width / original_width
        elif height:
            scale = height / original_height
        else:
            scale = 1.0

        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        drawing.hAlign = align

        self.story.append(Spacer(1, 15))
        self.story.append(drawing)
        self.story.append(Spacer(1, 15))

    def build(self) -> None:
        self.doc.build(
            self.story,
            onFirstPage=self._on_page,
            onLaterPages=self._on_page,
        )
