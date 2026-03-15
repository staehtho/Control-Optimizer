"""Formula label widget backed by LaTeX rendering."""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt

from utils import LatexRenderer


class FormulaWidget(QLabel):
    """Render a LaTeX formula into a QLabel pixmap."""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, formula: str = "", font_size_scale: float = 1, parent: QWidget = None):
        super().__init__(parent)

        self._formula = formula
        self._font_size_scale = font_size_scale

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._update_formula()

    # ============================================================
    # Public API
    # ============================================================

    def set_formula(self, formula: str) -> None:
        """Set the formula string and refresh the pixmap."""
        self._formula = formula
        self._update_formula()

    def set_font_size(self, font_size: float) -> None:
        """Set the font size scale and refresh the pixmap."""
        self._font_size_scale = font_size
        self._update_formula()

    # ============================================================
    # Internal helpers
    # ============================================================

    def _update_formula(self) -> None:
        """Render the current formula into a pixmap, if set."""
        if self._formula != "":
            self.setPixmap(LatexRenderer.latex2pixmap(self._formula, font_size_scale=self._font_size_scale))
