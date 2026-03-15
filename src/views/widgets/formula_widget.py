from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt

from utils import LatexRenderer


class FormulaWidget(QLabel):
    def __init__(self, formula: str = "", font_size_scale: float = 1, parent: QWidget = None):
        super().__init__(parent)

        self._formula = formula
        self._font_size_scale = font_size_scale

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._update_formula()

    def set_formula(self, formula: str) -> None:
        self._formula = formula
        self._update_formula()

    def set_font_size(self, font_size: float) -> None:
        self._font_size_scale = font_size
        self._update_formula()

    def _update_formula(self) -> None:
        if self._formula != "":
            self.setPixmap(LatexRenderer.latex2pixmap(self._formula, font_size_scale=self._font_size_scale))

