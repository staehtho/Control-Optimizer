from __future__ import annotations
from typing import List, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import StyleSheet1, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)
from reportlab.lib import colors
from svglib.svglib import svg2rlg


class BaseReport:
    def __init__(
        self,
        filename: str,
        pagesize: tuple[float, float] = A4,
        margin: int = 40
    ) -> None:
        self.filename: str = filename
        self.pagesize: tuple[float, float] = pagesize
        self.margin: int = margin

        self.styles: StyleSheet1 = getSampleStyleSheet()
        self.story: List[Flowable] = []

        self.doc: SimpleDocTemplate = SimpleDocTemplate(
            filename,
            pagesize=pagesize,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
        )

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

    def add_table(self, data: List[List[Any]]) -> None:
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

    def add_svg(self, svg_path: str, width: int = 400) -> None:
        drawing = svg2rlg(svg_path)
        scale = width / drawing.width
        drawing.scale(scale, scale)
        self.story.append(drawing)
        self.story.append(Spacer(1, 20))

    # ============================================================
    # Finalize PDF
    # ============================================================

    def build(self) -> None:
        self.doc.build(self.story)
