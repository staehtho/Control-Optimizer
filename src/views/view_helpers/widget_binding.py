"""Widget binding helpers for Qt views."""
from __future__ import annotations

from PySide6.QtWidgets import QAbstractButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox

from app_types import FieldType
from . import validation_helpers


# ============================================================
# Widget <-> ViewModel Synchronization
# ============================================================

def on_widget_changed(view, key: str | FieldType, attribute: str, *args, **kwargs) -> None:
    """Handle changes from widgets and update the corresponding attribute."""
    if view.initializing:
        return

    widget = view.field_widgets[key]
    validation_helpers.clear_input_error(widget)

    value = extract_widget_value(view, key, widget, *args, **kwargs)

    # Log the change
    view.logger.info(f"User changed {key}: {value}")

    # Set the final attribute to the new value
    set_attr_path(view, attribute, value)


def extract_widget_value(view, key: str | FieldType, widget, *args, **kwargs):
    """Extract a value from a supported widget type."""
    if isinstance(widget, QComboBox):
        # For QComboBox, Qt signals pass the index
        index = args[0] if args else widget.currentIndex()
        return widget.itemData(index)

    if isinstance(widget, QLineEdit):
        text = widget.text()
        value_type = kwargs.get("value_type", str)  # default to str if not provided
        try:
            return value_type(text)
        except (ValueError, TypeError):
            # Handle invalid input gracefully
            view.logger.warning(f"Cannot convert '{text}' to {value_type} for widget '{key}'")
            widget.setText(f"{text}")
            return text

    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        return widget.value()

    if isinstance(widget, QAbstractButton) and widget.isCheckable():
        return widget.isChecked()

    view.logger.warning(f"Widget type {type(widget)} not handled for key '{key}'")
    return None


def set_attr_path(root, attribute: str, value) -> None:
    """Traverse a dotted attribute path on root and set its final value."""
    attrs = attribute.split(".")
    attr = root
    for attr_name in attrs[:-1]:
        attr = getattr(attr, attr_name)
    setattr(attr, attrs[-1], value)


def format_value(value):
    """Format values for display, using scientific notation for extreme floats."""
    if isinstance(value, float):
        if value == 0.0:
            return "0.0"
        if abs(value) >= 1e4 or abs(value) < 1e-3:
            return f"{value:.1e}"

    return str(value)


def on_vm_changed(view, key: str | FieldType, attribute: str) -> None:
    """Update a widget to reflect the current value of its corresponding attribute."""
    # Traverse dotted attribute path
    attr = view
    for attr_name in attribute.split("."):
        attr = getattr(attr, attr_name)
    value = attr

    # Log the update
    view.logger.debug(f"Updating widget '{key}' to value: {value}")

    widget = view.field_widgets.get(key)
    if widget is None:
        view.logger.warning(f"No widget found for key '{key}'")
        return

    # A successful VM update indicates a valid state for this field.
    # Clear potential stale validation visuals/tooltips.
    validation_helpers.clear_input_error(widget)

    # Format value if necessary
    formatted_value = format_value(value)

    # Update based on widget type
    if isinstance(widget, QComboBox):
        current_value = widget.currentData()
        if current_value != value:
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)

    elif isinstance(widget, QLineEdit):
        text_value = str(formatted_value)
        if widget.text() != text_value:
            widget.setText(text_value)

    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        if widget.value() != value:
            widget.setValue(value)

    elif isinstance(widget, QAbstractButton) and widget.isCheckable():
        if widget.isChecked() != bool(value):
            widget.setChecked(bool(value))

    else:
        view.logger.warning(
            f"Widget type '{type(widget)}' not handled for key '{key}'"
        )
