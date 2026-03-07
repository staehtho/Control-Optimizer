import logging
from weakref import WeakSet
from PySide6.QtWidgets import (
    QWidget, QLayout, QLabel, QComboBox, QGridLayout, QFrame, QVBoxLayout, QLineEdit, QCheckBox, QSpinBox,
    QDoubleSpinBox, QScrollArea, QApplication
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from dataclasses import dataclass
from typing import Type, ClassVar, Optional

from app_domain.ui_context import UiContext
from views.translations import Translation


@dataclass
class FieldConfig:
    key: str
    widget_type: Type[QWidget] = QLabel
    create_label: bool = True


@dataclass
class SectionConfig:
    key: str
    fields: list[FieldConfig]

class BaseView:
    """
    Base class for all Views in the application.

    Responsibilities:
    - Bind to LanguageViewModel for UI translations
    - Provide a logger for debugging
    - Structured lifecycle: UI creation, signals, ViewModel bindings
    - Abstract methods enforce that concrete Views implement required functionality
    """

    _instances: ClassVar[WeakSet] = WeakSet()
    _active_theme: ClassVar[str] = "dark"
    _themes: ClassVar[dict[str, str]] = {}

    @classmethod
    def load_themes(cls, themes: dict[str, str], active_theme: str) -> None:
        cls._themes = dict(themes)
        if not cls._themes:
            raise ValueError("No themes provided")

        cls._active_theme = active_theme if active_theme in cls._themes else next(iter(cls._themes))

    def __init__(self, ui_context: "UiContext"):
        self._ui_context = ui_context

        self._initializing = True
        # -----------------------------
        # Language support
        # -----------------------------
        # Store reference to the LanguageViewModel
        self._vm_lang = self._ui_context.vm_lang
        self._enum_translation = Translation()
        # Connect signal: whenever language changes, call _retranslate
        self._vm_lang.languageChanged.connect(self._retranslate)

        # Scale factor for rendering the LaTeX formula
        self._formula_font_size_scale = 1.5
        self._dec = 3
        self._title_size = 16

        self._widgets = {}
        self._labels = {}

        BaseView._instances.add(self)
        # -----------------------------
        # Logging setup
        # -----------------------------
        self._logger = logging.getLogger(f"View.{self.__class__.__name__}.{id(self)}")
        self._logger.debug(f"{self.__class__.__name__} initialized")

        # -----------------------------
        # View lifecycle
        # -----------------------------
        # Step 1: Initialize UI components (widgets, layouts, etc.)
        self._init_ui()
        self.apply_theme()
        self._logger.debug("UI initialized")

        # Step 2: Connect UI signals (buttons, inputs, etc.)
        self._connect_signals()
        self._logger.debug("UI signals connected")

        # Step 3: Bind ViewModel signals to the View
        self._bind_vm()
        self._logger.debug("ViewModel bindings set up")

        # Step 4: Initial translation
        # Call _retranslate explicitly because the signal only fires on changes,
        # ensuring UI shows the correct initial language
        self._retranslate()
        self._logger.debug("initial translation applied")

        # Step 5: Apply initial value
        self._apply_init_value()

        self._initializing = False
        self._logger.debug("Initialization complete")

    # ---------- Lifecycle abstract methods ----------

    def _init_ui(self) -> None:
        """Create and configure UI elements (widgets, layouts, etc.)."""
        raise NotImplementedError

    def _connect_signals(self) -> None:
        """Connect UI signals (buttons, input fields, etc.) to handlers."""
        raise NotImplementedError

    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View updates (model â†’ view)."""
        raise NotImplementedError

    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        raise NotImplementedError

    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        raise NotImplementedError

    def _clear_layout(self, layout: QLayout) -> None:
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.hide()
                    widget.deleteLater()
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def _apply_title_property(self, lbl: QLabel, font_size: int = 0) -> None:
        font = QFont()
        font.setPointSize(self._title_size if font_size == 0 else font_size)  # size in pt
        font.setBold(True)
        lbl.setFont(font)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        if font_size == 0:
            lbl.setObjectName("viewTitle")
        else:
            lbl.setObjectName("sectionTitle")

    @staticmethod
    def _cmb_add_item(cmb: QComboBox, data: dict) -> None:
        current_data = cmb.currentData()
        cmb.clear()

        # alphabetisch nach Wert sortieren (case-insensitive)
        sorted_items = sorted(data.items(), key=lambda kv: kv[1].lower())

        for enum_key, text in sorted_items:
            cmb.addItem(text, enum_key)

        # alten Wert wieder auswählen, falls noch gültig
        if current_data in data:
            index = cmb.findData(current_data)
            if index >= 0:
                cmb.setCurrentIndex(index)

    def _create_grid(self, fields: list[FieldConfig | SectionConfig], columns: int = 4) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        parent_widget = self if isinstance(self, QWidget) else None

        for col in range(columns):
            layout.setColumnStretch(col, 1)  # all columns get equal stretch

        for field in fields:
            if isinstance(field, SectionConfig):
                frame = QFrame(parent_widget)
                frame.setObjectName("card")

                frame_layout = QVBoxLayout(frame)
                label = QLabel(frame)
                self._apply_title_property(label, int(self._title_size * 0.75))
                frame_layout.addWidget(label)
                self._labels[field.key] = label

                inner_layout = self._create_grid(field.fields, 2)
                frame_layout.addLayout(inner_layout)

                # Calculate inner rows
                inner_rows = len(field.fields) + 1

                # Find first empty position for section
                row = 1
                col = 0
                while self.cell_has_widget(layout, row, col):
                    col += 2
                    if col >= columns:
                        col = 0
                        row += 1

                layout.addWidget(frame, row, col, inner_rows, 2)

            else:
                # Normal field
                row = 1
                col = 0
                while self.cell_has_widget(layout, row, col):
                    col += 2
                    if col >= columns:
                        col = 0
                        row += 1

                try:
                    widget: QWidget = field.widget_type(parent=parent_widget)
                except TypeError:
                    widget = field.widget_type()
                    if parent_widget is not None and widget.parent() is None:
                        widget.setParent(parent_widget)
                if isinstance(widget, QLineEdit):
                    widget.setValidator(QDoubleValidator())

                self._widgets[field.key] = widget

                if field.create_label:
                    label = QLabel(parent_widget)
                    layout.addWidget(label, row, col)
                    self._labels[field.key] = label

                    layout.addWidget(widget, row, col + 1)
                else:
                    layout.addWidget(widget, row, col, 1, 2)


        return layout

    @staticmethod
    def cell_has_widget(grid_layout: QGridLayout, row: int, col: int) -> bool:
        item = grid_layout.itemAtPosition(row, col)
        return item is not None and item.widget() is not None

    @staticmethod
    def _create_page_layout() -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        return layout

    @staticmethod
    def _create_card(parent: Optional[QWidget] = None, expand_vertically_when_expanded: bool = False) -> tuple[
        QFrame, QVBoxLayout]:
        from views.widgets import ExpandableFrame

        frame = ExpandableFrame(
            expanded=True,
            expand_vertically_when_expanded=expand_vertically_when_expanded,
            parent=parent
        )
        frame.setObjectName("card")
        frame_layout = frame.content_layout()
        frame_layout.setContentsMargins(16, 14, 16, 14)
        frame_layout.setSpacing(10)
        return frame, frame_layout

    @staticmethod
    def _create_plain_card(parent: Optional[QWidget] = None) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(parent)
        frame.setObjectName("card")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 14, 16, 14)
        frame_layout.setSpacing(10)
        return frame, frame_layout

    @staticmethod
    def _wrap_in_scroll_area(content_widget: QWidget) -> QScrollArea:
        scroll = QScrollArea(content_widget.parentWidget())
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setWidget(content_widget)
        return scroll

    def apply_theme(self) -> None:
        widget = self if isinstance(self, QWidget) else None
        if widget is None:
            return
        if not BaseView._themes:
            return

        widget.setObjectName("viewRoot")
        fallback_theme = next(iter(BaseView._themes.values()))
        theme = BaseView._themes.get(BaseView._active_theme, fallback_theme)
        widget.setStyleSheet(theme)
        app = QApplication.instance()
        if app is not None:
            app.setProperty("appTheme", BaseView._active_theme)

        self._on_theme_applied()

    def _on_theme_applied(self) -> None:
        """Hook for subclasses that need non-QSS theme updates."""
        ...

    @classmethod
    def set_theme(cls, theme: str) -> None:
        if theme not in cls._themes:
            raise ValueError(f"Unknown theme '{theme}'. Valid themes: {', '.join(cls._themes.keys())}")

        cls._active_theme = theme

        for view in list(cls._instances):
            view.apply_theme()

    def _on_widget_changed(self, key: str, attribute: str, *args, **kwargs) -> None:
        """Handle changes from various input widgets and update the corresponding attribute.

        This method supports QComboBox, QLineEdit, QSpinBox, and similar widgets.
        It automatically retrieves the new value and sets the target attribute
        indicated by the dotted path `attribute`.

        Args:
            key (str): The key identifying the widget in self._widgets.
            attribute (str): The dotted path to the attribute to update
                             (e.g., "_vm_controller.anti_windup").
            *args: Additional arguments passed by the Qt signal (e.g., index for QComboBox).
        """
        if self._initializing:
            return

        widget = self._widgets[key]

        # Determine new value based on widget type
        if isinstance(widget, QComboBox):
            # For QComboBox, Qt signals pass the index
            index = args[0] if args else widget.currentIndex()
            value = widget.itemData(index)

        elif isinstance(widget, QLineEdit):
            text = widget.text()
            value_type = kwargs.get("value_type", str)  # default to str if not provided
            try:
                # Cast text to the specified type
                value = value_type(text)
            except (ValueError, TypeError):
                # Handle invalid input gracefully
                self._logger.warning(f"Cannot convert '{text}' to {value_type} for widget '{key}'")
                widget.setText(f"{text:.{self._dec}}")
                value = text

        elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            value = widget.value()

        elif isinstance(widget, QCheckBox):
            value = widget.isChecked()

        else:
            # Default fallback
            value = None
            self._logger.warning(f"Widget type {type(widget)} not handled for key '{key}'")

        # Log the change
        self._logger.info(f"User changed {key}: {value}")

        # Traverse the dotted attribute path to get the target object
        attrs = attribute.split(".")
        attr = self
        for attr_name in attrs[:-1]:
            attr = getattr(attr, attr_name)

        # Set the final attribute to the new value
        setattr(attr, attrs[-1], value)

    def _on_vm_changed(self, key: str, attribute: str) -> None:
        """Update a widget to reflect the current value of its corresponding attribute.

        This universal method automatically updates widgets of different types
        (QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox) based on
        the current value of the attribute in the model or view-model.

        Args:
            key (str): The key identifying the widget in self._widgets.
            attribute (str): The dotted path to the attribute to read
                             (e.g., "_vm_controller.anti_windup").
        """
        # Traverse the dotted attribute path to get the current value
        attr = self
        for attr_name in attribute.split("."):
            attr = getattr(attr, attr_name)
        value = attr

        # Log the update
        self._logger.debug(f"Updating widget '{key}' to value: {value}")

        widget = self._widgets.get(key)
        if widget is None:
            self._logger.warning(f"No widget found for key '{key}'")
            return

        # Update based on widget type
        if isinstance(widget, QComboBox):
            current_value = widget.currentData()
            if current_value != value:
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)

        elif isinstance(widget, QLineEdit):
            if widget.text() != str(value):
                if isinstance(value, float):
                    value = round(value, self._dec)
                widget.setText(str(value))

        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            if widget.value() != value:
                widget.setValue(value)

        elif isinstance(widget, QCheckBox):
            if widget.isChecked() != bool(value):
                widget.setChecked(bool(value))

        else:
            self._logger.warning(f"Widget type '{type(widget)}' not handled for key '{key}'")

