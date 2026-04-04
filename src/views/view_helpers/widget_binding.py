from __future__ import annotations

import inspect
from typing import Callable, Any, TYPE_CHECKING

from PySide6.QtWidgets import QAbstractButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QWidget

from app_types import FieldType
from . import validation_helpers

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from app_types import ConnectSignalConfig

# ============================================================
# Widget <-> ViewModel Synchronization
# ============================================================
def connect_signal(view, config: ConnectSignalConfig) -> None:
    """Connect a signal to a configurable event handling pipeline.

    This function dynamically connects a signal from a widget (or any QObject)
    to a wrapper callback that supports four execution modes:

    1. Override handler:
        If ``override_event_handler`` is defined, it is called and no other
        handlers are executed.
    2. Pre-handler:
        If ``pre_event_handler`` is defined, it is executed before the
        main handler.
    3. Main handler:
        The ``main_event_handler`` is called to perform the default processing
        (e.g., updating the ViewModel or UI).
    4. Post-handler:
        If ``post_event_handler`` is defined, it is executed after the
        main handler.

    Execution order:
        override → (pre → main → post)

    Notes:
        - If override handler is provided, pre/main/post are skipped.
        - The main handler must be defined unless an override is provided.
    """

    def _call_handler(handler: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Safely invoke a handler with only the arguments it can accept."""
        sig = inspect.signature(handler)

        params = list(sig.parameters.values())
        has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
        has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)

        # --- Selective binding ---
        accepted_args = []
        accepted_kwargs = {}
        consumed_names = set()

        # Positional parameters
        positional_params = [
            p for p in params
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]

        for i, param in enumerate(positional_params):
            if i < len(args):
                accepted_args.append(args[i])
                consumed_names.add(param.name)
            elif param.name in kwargs:
                if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                    continue
                accepted_kwargs[param.name] = kwargs[param.name]
                consumed_names.add(param.name)

        # Extra positional parameters
        if has_var_positional and len(args) > len(positional_params):
            accepted_args.extend(args[len(positional_params):])

        # Keyword-only parameters
        for param in params:
            if param.kind == param.KEYWORD_ONLY and param.name in kwargs:
                accepted_kwargs[param.name] = kwargs[param.name]
                consumed_names.add(param.name)

        # Extra keyword parameters for **kwargs
        if has_var_keyword:
            positional_only_names = {
                p.name for p in positional_params if p.kind == inspect.Parameter.POSITIONAL_ONLY
            }
            for name, value in kwargs.items():
                if name in consumed_names or name in positional_only_names:
                    continue
                accepted_kwargs[name] = value

        return handler(*accepted_args, **accepted_kwargs)

    def _wrapper(*args):
        """Internal callback executed when the Qt signal is emitted.

        Applies the configured handling strategy:
        override → pre → main → post

        Args:
            *args: Positional arguments emitted by the Qt signal.
        """
        # --- 1. Override handler ---
        if config.override_event_handler is not None:
            _call_handler(config.override_event_handler, *args, **config.kwargs)
            return

        # --- 2. Pre-handler ---
        if config.pre_event_handler is not None:
            _call_handler(config.pre_event_handler, *args, **config.kwargs)

        # --- 3. Main handler ---
        if config.main_event_handler is not None:
            config.main_event_handler(
                view,
                config.widget,
                config.key,
                config.attr_name,
                *args,
                **config.kwargs,
            )
        else:
            raise ValueError("No main_event_handler defined in config")

        # --- 4. Post-handler ---
        if config.post_event_handler is not None:
            _call_handler(config.post_event_handler, *args, **config.kwargs)

    # Connect the Qt signal to the wrapper
    getattr(config.widget, config.signal_name).connect(_wrapper)


def on_widget_changed(view, widget: QObject, key: str | FieldType, attribute: str, *args, **kwargs) -> None:
    """Handle changes from widgets and update the corresponding attribute."""
    if not isinstance(widget, QWidget):
        raise TypeError(f"Expected QWidget, got {type(widget)}")

    if view.initializing:
        return

    validation_helpers.clear_input_error(widget)

    value = extract_widget_value(view, key, widget, *args, **kwargs)

    # Log the change
    view.logger.info(f"User changed {key}: {value}")

    # Set the final attribute to the new value
    set_attr_path(view, attribute, value)


def extract_widget_value(view, key: str | FieldType, widget: QWidget, *args, **kwargs):
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

    if hasattr(widget, "isChecked") and callable(getattr(widget, "isChecked")):
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


def format_value(value) -> str:
    """Format values for display, using scientific notation for extreme floats."""
    if isinstance(value, float):
        if value == 0.0:
            return "0.0"
        if abs(value) >= 1e4 or abs(value) < 1e-3:
            return f"{value:.1e}"

    return str(value)


def on_vm_changed(view, widget: QObject, key: str | FieldType, attribute: str, *args, **kwargs) -> None:
    """Update a widget to reflect the current value of its corresponding attribute."""
    # Traverse dotted attribute path
    attr = widget
    for attr_name in attribute.split("."):
        if not hasattr(attr, attr_name):
            raise AttributeError(f"'{attr_name}' not found in widget '{key}'")
        attr = getattr(attr, attr_name)
    value = attr

    # Log the update
    view.logger.debug(f"Updating widget '{key}' to value: {value}")

    field = kwargs.get("field")
    if not isinstance(field, QWidget) or field is None:
        raise TypeError(f"Expected QWidget, got {type(field)}")

    # A successful VM update indicates a valid state for this field.
    # Clear potential stale validation visuals/tooltips.
    validation_helpers.clear_input_error(field)

    # Format value if necessary
    formatted_value = format_value(value)

    # Update based on widget type
    if isinstance(field, QComboBox):
        current_value = field.currentData()
        if current_value != value:
            index = field.findData(value)
            if index >= 0:
                field.setCurrentIndex(index)

    elif isinstance(field, QLineEdit):
        text_value = str(formatted_value)
        if text_value == "None":
            text_value = ""
        field.setText(text_value)
        if field.text() != text_value:
            field.setText(text_value)

    elif isinstance(field, (QSpinBox, QDoubleSpinBox)):
        value_type = kwargs.get("value_type", str)
        if field.value() != value:
            field.setValue(value_type(value))

    elif isinstance(field, QAbstractButton) and field.isCheckable():
        if field.isChecked() != bool(value):
            field.setChecked(bool(value))

    else:
        view.logger.warning(
            f"Widget type '{type(field)}' not handled for key '{key}'"
        )


def on_vm_changed_old(view, key: str | FieldType, attribute: str) -> None:
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
        if text_value == "None":
            text_value = ""
        widget.setText(text_value)
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
