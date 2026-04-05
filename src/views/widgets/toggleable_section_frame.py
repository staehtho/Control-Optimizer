from PySide6.QtCore import Property, Signal, Slot, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from .section_frame import SectionFrame
from .toggle_switch import ToggleSwitch


class ToggleableSectionFrame(SectionFrame):
    """Section frame with a toggle that enables/disables the content."""

    activeChanged = Signal(bool)

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
            self,
            title: str = "",
            active: bool = True,
            parent: QWidget | None = None,
    ):
        self._active = bool(active)
        super().__init__(title=title, parent=parent)
        self._inactive_effect = QGraphicsOpacityEffect(self.content_widget)
        self._inactive_effect.setOpacity(1.0)
        self.content_widget.setGraphicsEffect(self._inactive_effect)
        self._apply_active_state(self._active)

    # ============================================================
    # UI Construction
    # ============================================================

    def _create_header_widget(self, title: str) -> QWidget:
        """Create the header row containing the toggle and title."""
        widget = QWidget(self)
        widget.setFixedHeight(44)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._toggle_switch = ToggleSwitch(parent=widget)
        self._toggle_switch.setChecked(self._active)
        self._toggle_switch.toggled.connect(self._on_toggle_toggled)
        layout.addWidget(self._toggle_switch, 0)

        self._title_label = QLabel(title, widget)
        self._title_label.setObjectName("sectionTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._title_label, 1)

        return widget

    # ============================================================
    # Active State API
    # ============================================================

    def is_active(self) -> bool:
        """Return whether the content area is active."""
        return self._active

    def isChecked(self) -> bool:
        """Qt-style checked state alias for active."""
        return self._toggle_switch.isChecked()

    @Slot(bool)
    def set_active(self, value: bool) -> None:
        """Enable or disable the content area."""
        value = bool(value)
        if value == self._active:
            return

        self._active = value
        self._apply_active_state(value)
        self._sync_toggle_checked(value)
        self.activeChanged.emit(value)

    def setChecked(self, checked: bool) -> None:
        """Qt-style setter for checked/active state."""
        self.set_active(checked)

    def set_checked_no_anim(self, checked: bool) -> None:
        """Force state without running the toggle animation."""
        was_blocked = self.blockSignals(True)
        try:
            self._toggle_switch.set_checked_no_anim(bool(checked))
            if bool(checked) != self._active:
                self._active = bool(checked)
                self._apply_active_state(self._active)
        finally:
            self.blockSignals(was_blocked)

    active = Property(bool, is_active, set_active, notify=activeChanged)

    # ============================================================
    # Internal helpers
    # ============================================================
    def _on_toggle_toggled(self, checked: bool) -> None:
        self.set_active(checked)

    def _apply_active_state(self, active: bool) -> None:
        self.content_widget.setEnabled(active)
        self._inactive_effect.setOpacity(1.0 if active else 0.45)

    def _sync_toggle_checked(self, active: bool) -> None:
        if self._toggle_switch.isChecked() == active:
            return
        self._toggle_switch.blockSignals(True)
        self._toggle_switch.setChecked(active)
        self._toggle_switch.blockSignals(False)
