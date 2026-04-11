from enum import Enum
from PySide6.QtCore import (
    Property, QPropertyAnimation, QEasingCurve, QRectF, QSize, Qt, Signal, Slot
)
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractButton


class TextPosition(Enum):
    Left = 0
    Right = 1


class ToggleSwitch(QAbstractButton):
    """A QSS‑themeable toggle switch with animated thumb."""

    trackColorChanged = Signal()
    thumbColorChanged = Signal()
    textColorChanged = Signal()

    def __init__(self, text: str = "", text_position: TextPosition = TextPosition.Right, parent=None):
        super().__init__(parent)

        self.setObjectName("ToggleSwitch")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        self._text_position = text_position
        self._offset = 1.0 if self.isChecked() else 0.0

        # Default fallback colors (valid QColor objects)
        self._trackColor = QColor("#4b5563")
        self._thumbColor = QColor("#ffffff")
        self._textColor = QColor("#e2e8f0")

        # Animation
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

        self.toggled.connect(self._animate_toggle)

    # -----------------------------
    # Q_PROPERTY definitions
    # -----------------------------
    def getTrackColor(self):
        return self._trackColor

    def setTrackColor(self, v):
        if isinstance(v, QColor):
            self._trackColor = v
            self.update()
            self.trackColorChanged.emit()

    trackColor = Property(QColor, getTrackColor, setTrackColor, notify=trackColorChanged)

    def getThumbColor(self):
        return self._thumbColor

    def setThumbColor(self, v):
        if isinstance(v, QColor):
            self._thumbColor = v
            self.update()
            self.thumbColorChanged.emit()

    thumbColor = Property(QColor, getThumbColor, setThumbColor, notify=thumbColorChanged)

    def getTextColor(self):
        return self._textColor

    def setTextColor(self, v):
        if isinstance(v, QColor):
            self._textColor = v
            self.update()
            self.textColorChanged.emit()

    textColor = Property(QColor, getTextColor, setTextColor, notify=textColorChanged)

    # -----------------------------
    # Layout
    # -----------------------------
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

    # -----------------------------
    # Painting
    # -----------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        track_w = 36
        track_h = 20
        radius = track_h / 2
        spacing = 6

        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self.text()) if self.text() else 0

        # Track position
        if self.text() and self._text_position == TextPosition.Left:
            track_x = text_w + spacing
            text_x = 0
        else:
            track_x = 0
            text_x = track_w + spacing

        y = (rect.height() - track_h) / 2
        track_rect = QRectF(track_x, y, track_w, track_h)

        # Draw track
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._trackColor)
        painter.drawRoundedRect(track_rect, radius, radius)

        # Thumb
        margin = 2
        thumb_d = track_h - 2 * margin
        max_x = track_w - 2 * margin - thumb_d
        thumb_x = track_rect.x() + margin + self._offset * max_x
        thumb_rect = QRectF(thumb_x, track_rect.y() + margin, thumb_d, thumb_d)

        painter.setBrush(self._thumbColor)
        painter.drawEllipse(thumb_rect)

        # Text
        if self.text():
            painter.setPen(self._textColor)
            text_rect = QRectF(text_x, 0, rect.width() - text_x, rect.height())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())

    # -----------------------------
    # Animation
    # -----------------------------
    def _animate_toggle(self, checked: bool):
        self.setProperty("checked", checked)
        self.style().unpolish(self)
        self.style().polish(self)

        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    @Slot(bool)
    def set_checked_no_anim(self, checked: bool) -> None:
        """Force state without running the toggle animation."""
        self._animation.stop()
        was_blocked = self.blockSignals(True)
        try:
            self.setChecked(checked)
            self.set_offset(1.0 if checked else 0.0)
        finally:
            self.blockSignals(was_blocked)

    # -----------------------------
    # Offset property
    # -----------------------------
    def get_offset(self):
        return self._offset

    def set_offset(self, value: float):
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)