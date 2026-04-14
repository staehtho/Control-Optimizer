from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Any
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
    QHBoxLayout,
    QToolButton,
    QSizePolicy,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, Qt, QObject, QCoreApplication, QT_TRANSLATE_NOOP

from views.translations import Translation
from views.view_helpers import layout_helpers, widget_binding, validation_helpers, icon_helpers
from resources.resources import Icons

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from app_types import FieldType, FieldConfig, SectionConfig, ConnectSignalConfig


class NavigationSignals(QObject):
    """Signals used by views that support step navigation.

    Attributes:
        nextRequested (Signal): Emitted when the user requests the next step.
        previousRequested (Signal): Emitted when the user requests the previous step.
    """

    nextRequested = Signal()
    previousRequested = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)


class ViewMixin:
    """Mixin for Qt views that supports localization, theming, and lifecycle hooks.

    Views that inherit this mixin must implement UI initialization, signal
    connection, ViewModel binding, translation, and initial value application.
    """

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, ui_context: UiContext):
        """Initialize the view mixin and run the view lifecycle.

        Args:
            ui_context (UiContext): Shared UI context containing theme,
                language, and settings ViewModels.
        """
        self._ui_context = ui_context
        self.nav_signals = NavigationSignals(self._as_widget())

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

        self._title_icon_size = 50
        self._nav_button_size = 32
        self._nav_icon_size = 20
        self._nav_buttons_initialized = False

        self._opacity_disabled = 0.45

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
        self._apply_theme()
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
        """Return self as a QWidget when available.

        Returns:
            Optional[QWidget]: The object cast as QWidget if possible, otherwise None.
        """
        return self if isinstance(self, QWidget) else None

    # ============================================================
    # Lifecycle Hooks
    # ============================================================

    def _init_ui(self) -> None:
        """Create and configure UI elements.

        Implementations should create widgets, layouts, and other visual
        components required by the view.
        """
        ...

    def _connect_signals(self) -> None:
        """Connect UI signals to view handlers.

        This includes button clicks, input changes, and other widget events.
        """
        ...

    def _bind_vm(self) -> None:
        """Bind ViewModel signals to view update methods.

        This method is responsible for connecting the model-to-view data flow.
        """
        ...

    def _retranslate(self) -> None:
        """Update all UI text values after a language change."""
        self._retranslate_nav_buttons()

    def _apply_init_value(self) -> None:
        """Apply initial values to widgets and controls."""
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
        layout_helpers.clear_layout(layout)

    @staticmethod
    def _create_page_layout() -> QVBoxLayout:
        """Create a standard page layout with consistent margins and spacing."""
        return layout_helpers.create_page_layout()

    @staticmethod
    def _create_card_layout() -> QVBoxLayout:
        """Create a standard card layout with consistent margins and spacing."""
        return layout_helpers.create_card_layout()

    @staticmethod
    def _create_card(
            title: str = "",
            toggleable: bool = False,
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

    def _create_navigation_buttons_layout(self, pre_btn: bool = True, next_btn: bool = True,
                                          parent: Optional[QWidget] = None) -> QHBoxLayout:
        """Create previous/next navigation buttons row."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addStretch()

        btn_parent = parent or self._as_widget() or None

        if pre_btn:
            self._btn_nav_previous = QToolButton(btn_parent)
            self._btn_nav_previous.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_nav_previous.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self._btn_nav_previous.setFixedSize(self._nav_button_size, self._nav_button_size)
            self._btn_nav_previous.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._btn_nav_previous.setObjectName("navPrevBtn")
            self._btn_nav_previous.clicked.connect(self.nav_signals.previousRequested.emit)
            layout.addWidget(self._btn_nav_previous)

        if next_btn:
            self._btn_nav_next = QToolButton(btn_parent)
            self._btn_nav_next.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_nav_next.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self._btn_nav_next.setFixedSize(self._nav_button_size, self._nav_button_size)
            self._btn_nav_next.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._btn_nav_next.setObjectName("navNextBtn")
            self._btn_nav_next.clicked.connect(self.nav_signals.nextRequested.emit)
            layout.addWidget(self._btn_nav_next)

        self._nav_buttons_initialized = True
        self._apply_nav_button_icons()
        self._retranslate_nav_buttons()

        return layout

    # ============================================================
    # Widget -> ViewModel Synchronization
    # ============================================================
    @staticmethod
    def _on_widget_changed(
            view: Any,
            widget: QObject,
            key: str | FieldType,
            attr_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> None:
        """Handle changes from various input widgets and update the corresponding attribute."""
        widget_binding.on_widget_changed(view, widget, key, attr_name, *args, **kwargs)

    def _connect_object_signals(self, configs: list[ConnectSignalConfig]) -> None:
        """Connect widgets or objects signal handlers."""
        for config in configs:
            widget_binding.connect_signal(self, config)

    @staticmethod
    def _format_value(value) -> str:
        """Format values for display, using scientific notation for extreme floats."""
        return widget_binding.format_value(value)

    @staticmethod
    def _on_vm_changed(
            view: Any,
            widget: QObject,
            key: str | FieldType,
            attr_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> None:
        """Update a widget to reflect the current value of its corresponding attribute."""
        widget_binding.on_vm_changed(view, widget, key, attr_name, *args, **kwargs)

    # ============================================================
    # Validation Handling
    # ============================================================

    def _on_validation_failed(self, field: FieldType, message: str) -> None:
        """Handle a validation error for a specific field."""
        validation_helpers.on_validation_failed(self, field, message)

    @staticmethod
    def _clear_input_error(widget: QWidget) -> None:
        """Restore a line edit to its normal state after invalid-input handling."""
        validation_helpers.clear_input_error(widget)

    # ============================================================
    # Theme Handling
    # ============================================================

    def _apply_theme(self) -> None:
        """Apply the current theme to the view and application.

        This method updates the view stylesheet and sets application-level
        theme properties used by child widgets and styles.
        """
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

        self._apply_nav_button_icons()
        self._on_theme_applied()

    def _on_theme_applied(self) -> None:
        """Hook for subclasses that need non-QSS theme updates.

        Subclasses can override this method to apply additional styling or
        widget updates that cannot be expressed via stylesheet alone.
        """
        ...

    def _on_theme_changed(self, *_args) -> None:
        """Respond to theme changes from the theme ViewModel."""
        self._apply_theme()

    # ============================================================
    # Icon Utilities
    # ============================================================

    def _load_icon(self, svg_path: str | Path, size: int = 24) -> QIcon:
        """Load and recolor an SVG icon according to the current theme.

        Args:
            svg_path (str | Path): Path to the SVG icon file.
            size (int): Desired icon size in pixels.

        Returns:
            QIcon: The themed icon instance.
        """
        return icon_helpers.load_icon(self._vm_theme.get_svg_color_map(), svg_path, size)

    # ============================================================
    # Navigation Buttons
    # ============================================================

    def _apply_nav_button_icons(self) -> None:
        if not self._nav_buttons_initialized:
            return
        if hasattr(self, "_btn_nav_previous"):
            self._btn_nav_previous.setIcon(self._load_icon(Icons.nav_previous, self._nav_icon_size))
        if hasattr(self, "_btn_nav_next"):
            self._btn_nav_next.setIcon(self._load_icon(Icons.nav_next, self._nav_icon_size))

    def _retranslate_nav_buttons(self) -> None:
        if not self._nav_buttons_initialized:
            return

        tr = lambda text: QCoreApplication.translate("ViewMixin", text) if text else text
        text_pre = QT_TRANSLATE_NOOP("ViewMixin", "Previous")
        text_next = QT_TRANSLATE_NOOP("ViewMixin", "Next")
        if hasattr(self, "_btn_nav_previous"):
            self._btn_nav_previous.setToolTip(tr(text_pre))
        if hasattr(self, "_btn_nav_next"):
            self._btn_nav_next.setToolTip(tr(text_next))

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
