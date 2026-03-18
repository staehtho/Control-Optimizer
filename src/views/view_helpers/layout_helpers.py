"""Layout creation and utility helpers for Qt views."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QLayout,
    QLabel,
    QGridLayout,
    QFrame,
    QVBoxLayout,
    QLineEdit,
    QScrollArea,
)
from PySide6.QtGui import Qt

from app_types import FieldConfig, SectionConfig


# ============================================================
# Layout Creation Utilities
# ============================================================

def create_grid(view, fields: list[FieldConfig | SectionConfig], columns: int = 4) -> QGridLayout:
    """Create a dynamic grid layout from FieldConfig and SectionConfig."""
    layout = QGridLayout()
    layout.setHorizontalSpacing(10)
    layout.setVerticalSpacing(10)
    layout.setContentsMargins(0, 0, 0, 0)
    parent_widget = view if isinstance(view, QWidget) else None

    for col in range(columns):
        layout.setColumnStretch(col, 1)  # all columns get equal stretch

    for field in fields:
        if isinstance(field, SectionConfig):
            add_section(view, layout, field, columns, parent_widget)
        else:
            add_field(view, layout, field, columns, parent_widget)

    return layout


def add_section(
        view,
        layout: QGridLayout,
        section: SectionConfig,
        columns: int,
        parent_widget: Optional[QWidget],
) -> None:
    frame = QFrame(parent_widget)
    frame.setObjectName("card")

    frame_layout = QVBoxLayout(frame)
    label = QLabel(frame)
    label.setObjectName("sectionTitle")
    frame_layout.addWidget(label)
    view.labels[section.key] = label

    inner_layout = create_grid(view, section.fields, section.columns)
    frame_layout.addLayout(inner_layout)

    # Calculate inner rows
    inner_rows = len(section)

    # Find first empty position for section
    row, col = find_next_cell(layout, columns)
    layout.addWidget(frame, row, col, inner_rows, 2)


def add_field(
        view,
        layout: QGridLayout,
        field: FieldConfig,
        columns: int,
        parent_widget: Optional[QWidget],
) -> None:
    row, col = find_next_cell(layout, columns)
    widget = create_widget(field, parent_widget)
    view.field_widgets[field.key] = widget

    if field.create_label:
        label = QLabel(parent_widget)
        layout.addWidget(label, row, col)
        view.labels[field.key] = label

        layout.addWidget(widget, row, col + 1)
    else:
        layout.addWidget(widget, row, col, 1, 2)


def create_widget(field: FieldConfig, parent_widget: Optional[QWidget]) -> QWidget:
    """Instantiate a widget from a FieldConfig, applying its validator if needed."""
    try:
        widget: QWidget = field.widget_type(parent=parent_widget)
    except TypeError:
        widget = field.widget_type()
        if parent_widget is not None and widget.parent() is None:
            widget.setParent(parent_widget)
    if isinstance(widget, QLineEdit):
        widget.setValidator(field.validator())
    return widget


def find_next_cell(layout: QGridLayout, columns: int) -> tuple[int, int]:
    """Find the next free (row, col) cell in the grid."""
    row = 1
    col = 0
    while cell_has_widget(layout, row, col):
        col += 2
        if col >= columns:
            col = 0
            row += 1
    return row, col


# ============================================================
# Layout Utilities
# ============================================================

def clear_layout(layout: QLayout) -> None:
    """Remove and delete all widgets/layouts from a layout."""
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
            elif item.layout() is not None:
                clear_layout(item.layout())


def cell_has_widget(grid_layout: QGridLayout, row: int, col: int) -> bool:
    """Check if a grid cell has a widget assigned."""
    item = grid_layout.itemAtPosition(row, col)
    return item is not None and item.widget() is not None


def create_page_layout() -> QVBoxLayout:
    """Create a standard page layout with consistent margins and spacing."""
    layout = QVBoxLayout()
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(14)
    return layout


def create_card(title: Optional[str], parent: Optional[QWidget] = None) -> tuple[QFrame, QVBoxLayout]:
    """Create a themed card container using SectionFrame."""
    from views.widgets import SectionFrame

    frame = SectionFrame(title=title, parent=parent)
    frame.setObjectName("card")
    frame_layout = frame.content_layout()
    frame_layout.setContentsMargins(16, 14, 16, 14)
    frame_layout.setSpacing(10)
    return frame, frame_layout


def create_plain_card(parent: Optional[QWidget] = None) -> tuple[QFrame, QVBoxLayout]:
    """Create a plain card container without a custom frame."""
    frame = QFrame(parent)
    frame.setObjectName("card")
    frame_layout = QVBoxLayout(frame)
    frame_layout.setContentsMargins(16, 14, 16, 14)
    frame_layout.setSpacing(10)
    return frame, frame_layout


def wrap_in_scroll_area(content_widget: QWidget) -> QScrollArea:
    """Wrap content inside a transparent scroll area."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("background: transparent;")
    scroll.viewport().setStyleSheet("background: transparent;")
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(content_widget)
    return scroll
