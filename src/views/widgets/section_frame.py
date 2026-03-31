"""Reusable section frame with header and content area."""

from PySide6.QtCore import Property, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from views.view_helpers import clear_layout

class SectionFrame(QFrame):
    """Card-like frame with a titled header and a content layout."""

    titleChanged = Signal(str)

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
            self,
            title: str = "",
            parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(4)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._header_widget = self._create_header_widget(title)

        self.content_widget = QWidget(self)
        self._content_layout = QVBoxLayout(self.content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(6)

        self._main_layout.addWidget(self._header_widget, 0, Qt.AlignmentFlag.AlignTop)
        self._main_layout.addWidget(self.content_widget)

        self.content_widget.setVisible(True)

    # ============================================================
    # UI Construction
    # ============================================================

    def _create_header_widget(self, title: str) -> QWidget:
        """Create the header row containing the section title."""
        widget = QWidget(self)
        widget.setFixedHeight(44)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._title_label = QLabel(title, widget)
        self._title_label.setObjectName("sectionTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._title_label)
        layout.addStretch()

        return widget

    # ============================================================
    # Content API
    # ============================================================

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the content area."""
        self._content_layout.addWidget(widget)

    def remove_widget(self, widget: QWidget) -> None:
        """Remove a widget from the content area."""
        self._content_layout.removeWidget(widget)

    def add_layout(self, layout) -> None:
        """Add a layout to the content area."""
        self._content_layout.addLayout(layout)

    def clear_layout(self) -> None:
        """Remove all layout elements from the content area."""
        clear_layout(self._content_layout)

    def content_layout(self) -> QVBoxLayout:
        """Return the content layout for direct manipulation."""
        return self._content_layout

    # ============================================================
    # Title API
    # ============================================================

    def _title(self) -> str:
        """Return the current title text."""
        return self._title_label.text()

    def setText(self, value: str) -> None:
        """Set the title text and emit titleChanged if it changed."""
        if value == self._title_label.text():
            return
        self._title_label.setText(value)
        self.titleChanged.emit(value)

    title = Property(str, _title, setText, notify=titleChanged)
