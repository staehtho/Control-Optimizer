from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import QRectF, QByteArray
from PySide6.QtGui import QPainter


class AspectRatioSvgWidget(QSvgWidget):
    def __init__(
            self,
            svg_file: str | None = None,
            svg_bytes: bytes | bytearray | None = None,
            initial_scale: float = 1.0,
    ):
        super().__init__()

        self._svg_file: str | None = None
        self._svg_bytes: bytes | None = None
        self.initial_scale = initial_scale

        if svg_bytes is not None:
            self.set_svg_bytes(svg_bytes)
        elif svg_file is not None:
            self.set_svg_file(svg_file)

    # -----------------------
    # Public API
    # -----------------------

    def set_svg_file(self, path: str):
        """Load SVG from file."""
        self._svg_file = path
        self._svg_bytes = None
        self.load(path)
        self.update()

    def set_svg_bytes(self, data: bytes | bytearray):
        """Load SVG from raw bytes."""
        self._svg_bytes = bytes(data)
        self._svg_file = None
        self.load(QByteArray(self._svg_bytes))
        self.update()

    def reload(self):
        """Reload the current SVG source."""
        if self._svg_bytes is not None:
            self.load(QByteArray(self._svg_bytes))
        elif self._svg_file is not None:
            self.load(self._svg_file)
        self.update()

    def set_initial_scale(self, scale: float):
        """Update the initial scale."""
        self.initial_scale = scale
        self.update()

    # -----------------------
    # Rendering
    # -----------------------

    def paintEvent(self, event):
        """Render SVG scaled and centered, preserving aspect ratio with initial_scale."""
        painter = QPainter(self)

        svg_size = self.renderer().defaultSize()
        if svg_size.width() == 0 or svg_size.height() == 0:
            super().paintEvent(event)
            return

        scaled_svg_width = svg_size.width() * self.initial_scale
        scaled_svg_height = svg_size.height() * self.initial_scale

        w, h = self.width(), self.height()
        scale = min(w / scaled_svg_width, h / scaled_svg_height)

        new_w = scaled_svg_width * scale
        new_h = scaled_svg_height * scale
        x = (w - new_w) / 2
        y = (h - new_h) / 2

        target_rect = QRectF(x, y, new_w, new_h)
        self.renderer().render(painter, target_rect)