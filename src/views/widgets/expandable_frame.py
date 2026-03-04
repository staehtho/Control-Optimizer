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
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy


# TODO: wenn shrink, dann immer gleiche höhe -> gleiche wie Titel
class ExpandableFrame(QFrame):
    toggled = Signal(bool)
    titleChanged = Signal(str)

    def __init__(
            self,
            title: str = "",
            expanded: bool = False,
            expand_vertically_when_expanded: bool = False,
            animation_duration_ms: int = 200,
            parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._max_widget_height = 16777215

        self._expanded = expanded
        self._expand_vertically_when_expanded = expand_vertically_when_expanded

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(4)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._header_widget = self._create_header_widget(title, expanded)

        self._content_widget = QWidget(self)
        self._content_widget.installEventFilter(self)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(6)

        self._main_layout.addWidget(self._header_widget, 0, Qt.AlignmentFlag.AlignTop)
        self._main_layout.addWidget(self._content_widget)

        self._animation = QPropertyAnimation(self._content_widget, b"maximumHeight", self)
        self._animation.setDuration(animation_duration_ms)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.finished.connect(self._on_animation_finished)

        self._update_toggle_text()
        self._apply_size_policy()
        if expanded:
            self._content_widget.setVisible(True)
            if self._expand_vertically_when_expanded:
                self._content_widget.setMaximumHeight(self._max_widget_height)
            else:
                self._content_widget.setMaximumHeight(self._content_height())
        else:
            self._content_widget.setVisible(False)
            self._content_widget.setMaximumHeight(0)

    def _create_header_widget(self, title: str, expanded: bool) -> QWidget:
        widget = QWidget()
        widget.setFixedHeight(44)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._title_label = QLabel(title, widget)
        self._title_label.setObjectName("sectionTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._toggle_btn = QPushButton(widget)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(expanded)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.toggled.connect(self.set_expanded)

        layout.addWidget(self._title_label)
        layout.addStretch()
        layout.addWidget(self._toggle_btn, 0, Qt.AlignmentFlag.AlignRight)

        return widget

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
        self._apply_size_policy()

        if expanded:
            self._content_widget.setVisible(True)

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
                and event.type() == QEvent.Type.LayoutRequest
                and self._expanded
                and self._animation.state() != QAbstractAnimation.State.Running
                and not self._expand_vertically_when_expanded
        ):
            self._content_widget.setMaximumHeight(self._content_height())
        return super().eventFilter(watched, event)

    def _content_height(self) -> int:
        return self._content_layout.sizeHint().height()

    def _refresh_expanded_height(self) -> None:
        if (
                self._expanded
                and self._animation.state() != QAbstractAnimation.State.Running
                and not self._expand_vertically_when_expanded
        ):
            self._content_widget.setMaximumHeight(self._content_height())

    def _update_toggle_text(self) -> None:
        self._toggle_btn.setText("-" if self._expanded else "+")

    def _on_animation_finished(self) -> None:
        # Keep heavy content (e.g., plots with minimum sizes) out of layout flow when collapsed.
        if not self._expanded:
            self._content_widget.setVisible(False)
            return

        if self._expand_vertically_when_expanded:
            self._content_widget.setMaximumHeight(self._max_widget_height)

    def _apply_size_policy(self) -> None:
        if self._expanded and self._expand_vertically_when_expanded:
            vertical_policy = QSizePolicy.Policy.Expanding
        elif self._expanded:
            vertical_policy = QSizePolicy.Policy.Maximum
        else:
            vertical_policy = QSizePolicy.Policy.Maximum

        self.setSizePolicy(QSizePolicy.Policy.Expanding, vertical_policy)
        self.updateGeometry()

    title = Property(str, title, set_title, notify=titleChanged)
