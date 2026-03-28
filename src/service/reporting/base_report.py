from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from svglib.svglib import svg2rlg


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

    def add_table(self, data):
        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ]
            )
        )
        self.story.append(table)
        self.story.append(Spacer(1, 15))

    def add_svg(self, svg_path: str, width: int = 500) -> None:
        drawing = svg2rlg(svg_path)

        scale = width / drawing.width
        drawing.scale(scale, scale)

        # Fix bounding box
        drawing.height *= scale
        drawing.width *= scale

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
