from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QLayout,
    QComboBox,
    QGridLayout,
    QFrame,
    QVBoxLayout,
    QApplication,
    QScrollArea,
)
from PySide6.QtGui import QIcon

from views.translations import Translation
from views.view_helpers import layout_helpers, widget_binding, validation_helpers, icon_helpers

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from app_types import FieldType, FieldConfig, SectionConfig


class ViewMixin:
    """Mixin for Qt views, intended to be combined with QWidget/QMainWindow/QDialog.

    Responsibilities:
    - Bind to LanguageViewModel for UI translations
    - Provide a logger for debugging
    - Structured lifecycle: UI creation, signals, ViewModel bindings
    - Abstract methods enforce that concrete Views implement required functionality
    """

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, ui_context: UiContext):
        """Initialize the view mixin and run the view lifecycle."""
        self._ui_context = ui_context

        self.initializing = True
        # -----------------------------
        # Language support
        # -----------------------------
        # Store reference to the LanguageViewModel
        self._vm_lang = self._ui_context.vm_lang
        self._enum_translation = Translation()
        # Connect signal: whenever language changes, call _retranslate
        self._vm_lang.languageChanged.connect(self._retranslate)

        # Theme support
        self._vm_theme = self._ui_context.vm_theme
        self._vm_theme.themeChanged.connect(self._on_theme_changed)

        # Scale factor for rendering the LaTeX formula
        self._formula_font_size_scale = 1.5

        self._titel_icon_size = 50

        self.field_widgets = {}
        self.labels = {}
        # -----------------------------
        # Logging setup
        # -----------------------------
        self.logger = logging.getLogger(f"View.{self.__class__.__name__}")
        self.logger.debug(f"{self.__class__.__name__} initialized")

        # -----------------------------
        # View lifecycle
        # -----------------------------
        # Step 1: Initialize UI components (widgets, layouts, etc.)
        self._init_ui()
        self.apply_theme()
        self.logger.debug("UI initialized")

        # Step 2: Connect UI signals (buttons, inputs, etc.)
        self._connect_signals()
        self.logger.debug("UI signals connected")

        # Step 3: Bind ViewModel signals to the View
        self._bind_vm()
        self.logger.debug("ViewModel bindings set up")

        # Step 4: Initial translation
        # Call _retranslate explicitly because the signal only fires on changes,
        # ensuring UI shows the correct initial language
        self._retranslate()
        self.logger.debug("initial translation applied")

        # Step 5: Apply initial value
        self._apply_init_value()

        self.initializing = False
        self.logger.debug("Initialization complete")

    def _as_widget(self) -> Optional[QWidget]:
        """Return self as QWidget if applicable, otherwise None."""
        return self if isinstance(self, QWidget) else None

    # ============================================================
    # Lifecycle Hooks
    # ============================================================

    def _init_ui(self) -> None:
        """Create and configure UI elements (widgets, layouts, etc.)."""
        ...

    def _connect_signals(self) -> None:
        """Connect UI signals (buttons, input fields, etc.) to handlers."""
        ...

    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View updates (model -> view)."""
        ...

    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        ...

    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        ...

    # ============================================================
    # Layout Creation
    # ============================================================

    def _create_grid(self, fields: list[FieldConfig | SectionConfig], columns: int = 4) -> QGridLayout:
        """Create a dynamic grid layout from FieldConfig and SectionConfig."""
        return layout_helpers.create_grid(self, fields, columns)

    # ============================================================
    # Layout Utilities
    # ============================================================

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        """Remove and delete all widgets/layouts from a layout."""
        return layout_helpers.clear_layout(layout)

    @staticmethod
    def _create_page_layout() -> QVBoxLayout:
        """Create a standard page layout with consistent margins and spacing."""
        return layout_helpers.create_page_layout()

    @staticmethod
    def _create_card(
            title: Optional[str] = "",
            toggleable: Optional[bool] = False,
            parent: Optional[QWidget] = None
    ) -> tuple[QFrame, QVBoxLayout]:
        """Create a themed card container using SectionFrame."""
        return layout_helpers.create_card(title, toggleable, parent)

    @staticmethod
    def _create_plain_card(parent: Optional[QWidget] = None) -> tuple[QFrame, QVBoxLayout]:
        """Create a plain card container without a custom frame."""
        return layout_helpers.create_plain_card(parent)

    @staticmethod
    def _wrap_in_scroll_area(content_widget: QWidget) -> QScrollArea:
        """Wrap content inside a transparent scroll area."""
        return layout_helpers.wrap_in_scroll_area(content_widget)

    # ============================================================
    # Widget ? ViewModel Synchronization
    # ============================================================

    def _on_widget_changed(self, widget: QWidget, key: str | FieldType, attribute: str, *args, **kwargs) -> None:
        """Handle changes from various input widgets and update the corresponding attribute."""
        return widget_binding.on_widget_changed(self, widget, key, attribute, *args, **kwargs)

    @staticmethod
    def _format_value(value):
        """Format values for display, using scientific notation for extreme floats."""
        return widget_binding.format_value(value)

    def _on_vm_changed(self, key: str | FieldType, attribute: str) -> None:
        """Update a widget to reflect the current value of its corresponding attribute."""
        return widget_binding.on_vm_changed(self, key, attribute)

    # ============================================================
    # Validation Handling
    # ============================================================

    def _on_validation_failed(self, field: FieldType, message: str) -> None:
        """Handle a validation error for a specific field."""
        return validation_helpers.on_validation_failed(self, field, message)

    @staticmethod
    def _clear_input_error(widget: QWidget) -> None:
        """Restore a line edit to its normal state after invalid-input handling."""
        return validation_helpers.clear_input_error(widget)

    # ============================================================
    # Theme Handling
    # ============================================================

    def apply_theme(self) -> None:
        """Apply the current theme to the view and application properties."""
        widget = self._as_widget()
        if widget is None:
            return

        widget.setObjectName("viewRoot")
        stylesheet = self._vm_theme.get_theme_stylesheet()
        if not stylesheet:
            return
        widget.setStyleSheet(stylesheet)
        app = QApplication.instance()
        if app is not None:
            app.setProperty("appTheme", self._vm_theme.current_theme)
            background = self._vm_theme.get_theme_background_color()
            text_color = self._vm_theme.get_theme_text_color()
            if text_color is not None:
                app.setProperty("themeTextColor", text_color)
            if background is not None:
                app.setProperty("themeBackgroundColor", background)

        self._on_theme_applied()

    def _on_theme_applied(self) -> None:
        """Hook for subclasses that need non-QSS theme updates."""
        ...

    def _on_theme_changed(self, *_args) -> None:
        """Apply the theme when the theme ViewModel changes."""
        self.apply_theme()

    # ============================================================
    # Icon Utilities
    # ============================================================

    def _load_icon(self, svg_path: str | Path, size: int = 24) -> QIcon:
        """Load an SVG icon and recolor it using the current theme."""
        return icon_helpers.load_icon(self._vm_theme.get_svg_color_map(), svg_path, size)

    # ============================================================
    # Internal Utilities
    # ============================================================

    @staticmethod
    def _cmb_add_item(cmb: QComboBox, data: dict) -> None:
        """Populate a combobox with a dict of enum->label items, preserving selection."""
        cmb.blockSignals(True)
        current_data = cmb.currentData()
        cmb.clear()

        # alphabetisch nach Wert sortieren (case-insensitive)
        sorted_items = sorted(data.items(), key=lambda kv: kv[1].lower())

        for enum_key, text in sorted_items:
            cmb.addItem(text, enum_key)

        # alten Wert wieder auswaehlen, falls noch gueltig
        if current_data in data:
            index = cmb.findData(current_data)
            if index >= 0:
                cmb.setCurrentIndex(index)
        cmb.blockSignals(False)
