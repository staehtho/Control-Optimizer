from PySide6.QtCore import Property, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SectionFrame(QFrame):
    titleChanged = Signal(str)

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

        self._content_widget = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(6)

        self._main_layout.addWidget(self._header_widget, 0, Qt.AlignmentFlag.AlignTop)
        self._main_layout.addWidget(self._content_widget)

        self._content_widget.setVisible(True)

    def _create_header_widget(self, title: str) -> QWidget:
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

    def add_widget(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._content_layout.addLayout(layout)

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def title(self) -> str:
        return self._title_label.text()

    def set_title(self, value: str) -> None:
        if value == self._title_label.text():
            return
        self._title_label.setText(value)
        self.titleChanged.emit(value)

    title = Property(str, title, set_title, notify=titleChanged)
