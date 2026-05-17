import math

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viewmodels import ThemeViewModel


class FigmaLoadingOverlay(QWidget):
    """Figma-style 3-dot loader that adapts to ThemeViewModel colors."""

    def __init__(self, theme_vm: ThemeViewModel, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._theme_vm = theme_vm
        self._t = 0.0

        # Update overlay when theme changes
        theme_vm.themeChanged.connect(self.update)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(16)

    def _advance(self):
        self._t += 0.05
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = self.rect().center()
        base_radius = max(6, min(self.width(), self.height()) // 30)

        # Theme colors from ViewModel
        bg_color = self._theme_vm.get_theme_background_color()
        dot_color = self._theme_vm.get_theme_text_color()

        # Soft translucent halo
        halo = QColor(bg_color)
        halo.setAlpha(70)
        painter.setBrush(halo)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, base_radius * 6, base_radius * 6)

        # Dot positions
        spacing = base_radius * 3
        offsets = [-spacing, 0, spacing]

        # Pulsing dots
        for i, dx in enumerate(offsets):
            phase = self._t + i * 0.4
            scale = 0.6 + 0.4 * math.sin(phase)

            c = QColor(dot_color)
            c.setAlpha(int(150 + 105 * (scale - 0.6)))

            painter.setBrush(c)
            painter.setPen(Qt.PenStyle.NoPen)

            r = base_radius * scale
            painter.drawEllipse(QPointF(center.x() + dx, center.y()), r, r)
