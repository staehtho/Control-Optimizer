from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter


class AspectRatioSvgWidget(QSvgWidget):
    def __init__(self, svg_file: str, initial_scale: float = 1.0):
        """
        svg_file: path to the SVG
        initial_scale: initial scaling factor applied to SVG size
                       (1.0 = native size, 0.5 = half size, 2.0 = double size)
        """
        super().__init__(svg_file)
        self.initial_scale = initial_scale

    def paintEvent(self, event):
        """Render SVG scaled and centered, preserving aspect ratio with initial_scale."""
        painter = QPainter(self)
        svg_size = self.renderer().defaultSize()
        if svg_size.width() == 0 or svg_size.height() == 0:
            super().paintEvent(event)
            return

        # Apply initial scale to SVG native size
        scaled_svg_width = svg_size.width() * self.initial_scale
        scaled_svg_height = svg_size.height() * self.initial_scale

        # Compute scale to fit widget while preserving aspect ratio
        w, h = self.width(), self.height()
        scale = min(w / scaled_svg_width, h / scaled_svg_height)

        new_w = scaled_svg_width * scale
        new_h = scaled_svg_height * scale
        x = (w - new_w) / 2
        y = (h - new_h) / 2

        target_rect = QRectF(x, y, new_w, new_h)
        self.renderer().render(painter, target_rect)
