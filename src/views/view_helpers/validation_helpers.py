"""Validation UI helpers for Qt views."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QLineEdit, QToolTip
from PySide6.QtCore import QPoint

from app_types import FieldType


# ============================================================
# Validation Handling
# ============================================================

def on_validation_failed(view, field: str | FieldType, message: str) -> None:
    """Handle a validation error for a specific field."""
    widget = view.field_widgets.get(field)

    if widget is None:
        return

    show_invalid_input(widget, message)


def show_invalid_input(widget: QLineEdit, message: str) -> None:
    """Show a consistent invalid-input state for line edits across all views."""
    if widget.property("_default_tooltip") is None:
        widget.setProperty("_default_tooltip", str(widget.toolTip() or ""))
    widget.setProperty("_input_invalid", True)
    widget.setStyleSheet("border: 1px solid #d9534f;")
    widget.setToolTip(message)
    QToolTip.showText(widget.mapToGlobal(QPoint(0, widget.height())), message, widget)


def clear_input_error(widget: QWidget) -> None:
    """Restore a line edit to its normal state after invalid-input handling."""
    if widget.property("_input_invalid") is not True:
        return

    widget.setStyleSheet("")
    default_tooltip = widget.property("_default_tooltip")
    if isinstance(default_tooltip, str):
        widget.setToolTip(default_tooltip)
    QToolTip.hideText()
    widget.setProperty("_input_invalid", False)
