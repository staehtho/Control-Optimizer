from PySide6.QtCore import Property, QPropertyAnimation, QEasingCurve, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import QAbstractButton, QSizePolicy


class ToggleSwitch(QAbstractButton):
    """Custom switch with a sliding thumb."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._offset = 1.0 if self.isChecked() else 0.0

        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._animate_toggle)

    def sizeHint(self) -> QSize:
        track_w = 36
        track_h = 20
        if self.text():
            fm = QFontMetrics(self.font())
            spacing = 6
            text_w = fm.horizontalAdvance(self.text())
            text_h = fm.height()
            return QSize(track_w + spacing + text_w, max(track_h, text_h))
        return QSize(track_w, track_h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        track_w = 36
        track_h = 20
        radius = track_h / 2
        y = (rect.height() - track_h) / 2
        track_rect = QRectF(0, y, track_w, track_h)

        palette = self.palette()
        if self.isChecked():
            track_color = palette.color(QPalette.ColorRole.Highlight)
        else:
            track_color = palette.color(QPalette.ColorRole.Button)
        if not self.isEnabled():
            track_color = QColor(track_color)
            track_color.setAlpha(120)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, radius, radius)

        margin = 2
        thumb_d = track_h - 2 * margin
        max_x = track_w - 2 * margin - thumb_d
        thumb_x = track_rect.x() + margin + self._offset * max_x
        thumb_rect = QRectF(thumb_x, track_rect.y() + margin, thumb_d, thumb_d)

        if self.isChecked():
            thumb_color = QColor(255, 255, 255)
        else:
            thumb_color = palette.color(QPalette.ColorRole.WindowText)
        if not self.isEnabled():
            thumb_color = QColor(thumb_color)
            thumb_color.setAlpha(140)

        painter.setBrush(thumb_color)
        painter.drawEllipse(thumb_rect)

        if self.text():
            text_color = palette.color(QPalette.ColorRole.WindowText)
            if not self.isEnabled():
                text_color = QColor(text_color)
                text_color.setAlpha(140)
            painter.setPen(text_color)
            text_x = track_w + 6
            text_rect = QRectF(text_x, 0, rect.width() - text_x, rect.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

    def _animate_toggle(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)
