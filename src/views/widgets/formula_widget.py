from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt

from utils import LatexRenderer


class FormulaWidget(QLabel):
    def __init__(self, formula: str, font_size_scale: float = 1, parent: QWidget = None):
        super().__init__(parent)

        self._font_size_scale = font_size_scale

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self.setPixmap(LatexRenderer.latex2pixmap(formula, font_size_scale=self._font_size_scale))
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    def set_formula(self, formula: str) -> None:
        self.setPixmap(LatexRenderer.latex2pixmap(formula, font_size_scale=self._font_size_scale))
