from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QObject,
    Property,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ExpandableFrame(QFrame):
    toggled = Signal(bool)
    titleChanged = Signal(str)

    def __init__(
            self,
            title: str = "",
            expanded: bool = False,
            animation_duration_ms: int = 200,
            parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self._expanded = expanded

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(4)

        self._header_widget = QWidget(self)
        header_layout = QHBoxLayout(self._header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self._title_label = QLabel(title, self._header_widget)

        self._toggle_btn = QPushButton(self._header_widget)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(expanded)
        self._toggle_btn.setFixedWidth(28)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.toggled.connect(self.set_expanded)

        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._toggle_btn, 0, Qt.AlignRight)

        self._content_widget = QWidget(self)
        self._content_widget.installEventFilter(self)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(6)

        self._main_layout.addWidget(self._header_widget)
        self._main_layout.addWidget(self._content_widget)

        self._animation = QPropertyAnimation(self._content_widget, b"maximumHeight", self)
        self._animation.setDuration(animation_duration_ms)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

        self._update_toggle_text()
        if expanded:
            self._content_widget.setMaximumHeight(self._content_height())
        else:
            self._content_widget.setMaximumHeight(0)

    def add_widget(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)
        self._refresh_expanded_height()

    def add_layout(self, layout) -> None:
        self._content_layout.addLayout(layout)
        self._refresh_expanded_height()

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def title(self) -> str:
        return self._title_label.text()

    def set_title(self, value: str) -> None:
        if value == self._title_label.text():
            return
        self._title_label.setText(value)
        self.titleChanged.emit(value)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded and self._toggle_btn.isChecked() == expanded:
            return

        self._expanded = expanded
        self._toggle_btn.setChecked(expanded)
        self._update_toggle_text()

        start_height = self._content_widget.maximumHeight()
        end_height = self._content_height() if expanded else 0

        self._animation.stop()
        self._animation.setStartValue(start_height)
        self._animation.setEndValue(end_height)
        self._animation.start()

        self.toggled.emit(expanded)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
                watched is self._content_widget
                and event.type() == QEvent.LayoutRequest
                and self._expanded
                and self._animation.state() != QAbstractAnimation.Running
        ):
            self._content_widget.setMaximumHeight(self._content_height())
        return super().eventFilter(watched, event)

    def _content_height(self) -> int:
        return self._content_layout.sizeHint().height()

    def _refresh_expanded_height(self) -> None:
        if self._expanded and self._animation.state() != QAbstractAnimation.Running:
            self._content_widget.setMaximumHeight(self._content_height())

    def _update_toggle_text(self) -> None:
        self._toggle_btn.setText("-" if self._expanded else "+")

    title = Property(str, title, set_title, notify=titleChanged)
