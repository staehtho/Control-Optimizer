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
from typing import Type, ClassVar

from viewmodels import LanguageViewModel
from views.translations import Translation


@dataclass
class FieldConfig:
    key: str
    widget_type: Type[QWidget] = QLabel


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
    _themes: ClassVar[dict[str, str]] = {
        "light": """
            QWidget {
                color: #17212b;
                font-size: 13px;
            }
            QWidget#viewRoot {
                background: #f4f7fb;
            }
            QFrame#card {
                background: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 14px;
                padding: 8px;
            }
            QLabel#viewTitle {
                color: #0f1d2d;
                font-size: 20px;
                font-weight: 700;
                padding: 4px 2px 8px 2px;
            }
            QLabel#sectionTitle {
                color: #1f2d3a;
                font-size: 15px;
                font-weight: 600;
                padding-bottom: 4px;
            }
            QLabel {
                background: transparent;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #c9d4e5;
                border-radius: 8px;
                min-height: 30px;
                padding: 4px 8px;
                selection-background-color: #2f80ed;
            }
            QComboBox {
                color: #17212b;
            }
            QComboBox::drop-down {
                border-left: 1px solid #dce3ee;
                background: #f4f7fb;
                width: 22px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #17212b;
                border: 1px solid #c9d4e5;
                selection-background-color: #2f80ed;
                selection-color: #ffffff;
            }
            QPushButton {
                background: #2f80ed;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                min-height: 32px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1d6cd7;
            }
            QPushButton:checked {
                background: #0d57ba;
            }
            QPushButton:disabled {
                background: #a8bddb;
                color: #e8eef8;
            }
            QTabWidget::pane {
                border: 1px solid #dce3ee;
                border-radius: 10px;
                background: #ffffff;
            }
            QTabBar::tab {
                background: #eaf0f8;
                border: 1px solid #dce3ee;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 14px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QProgressBar {
                background: #eaf0f8;
                border: 1px solid #dce3ee;
                border-radius: 8px;
                min-height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: #2f80ed;
            }
            QToolBar {
                background: #ffffff;
                border: 1px solid #dce3ee;
                border-radius: 8px;
                spacing: 6px;
                padding: 4px;
            }
            QToolButton {
                background: #f4f7fb;
                color: #17212b;
                border: 1px solid #dce3ee;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QToolButton:hover {
                background: #eaf0f8;
            }
            QToolButton:pressed {
                background: #dce7f7;
            }
            QToolBar QLineEdit {
                min-height: 26px;
            }
            QCheckBox {
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #c9d4e5;
                border-radius: 4px;
                background: #ffffff;
            }
            QCheckBox::indicator:checked {
                background: #2f80ed;
                border-color: #2f80ed;
            }
            QCheckBox::indicator:unchecked:hover {
                background: #f4f7fb;
                border-color: #9fb2cf;
            }
        """,
        "dark": """
            QWidget {
                color: #e2e8f0;
                font-size: 13px;
            }
            QWidget#viewRoot {
                background: #0f172a;
            }
            QFrame#card {
                background: #111827;
                border: 1px solid #2a3648;
                border-radius: 14px;
                padding: 8px;
            }
            QLabel#viewTitle {
                color: #f1f5f9;
                font-size: 20px;
                font-weight: 700;
                padding: 4px 2px 8px 2px;
            }
            QLabel#sectionTitle {
                color: #dbe6f5;
                font-size: 15px;
                font-weight: 600;
                padding-bottom: 4px;
            }
            QLabel {
                background: transparent;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: #0b1220;
                border: 1px solid #334155;
                border-radius: 8px;
                min-height: 30px;
                padding: 4px 8px;
                selection-background-color: #3b82f6;
            }
            QComboBox {
                color: #e2e8f0;
            }
            QComboBox::drop-down {
                border-left: 1px solid #334155;
                background: #1f2937;
                width: 22px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox QAbstractItemView {
                background: #111827;
                color: #e2e8f0;
                border: 1px solid #334155;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                min-height: 32px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton:checked {
                background: #1e40af;
            }
            QPushButton:disabled {
                background: #334155;
                color: #94a3b8;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 10px;
                background: #111827;
            }
            QTabBar::tab {
                background: #1f2937;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 14px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #111827;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QProgressBar {
                background: #1f2937;
                border: 1px solid #334155;
                border-radius: 8px;
                min-height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: #2563eb;
            }
            QToolBar {
                background: #111827;
                border: 1px solid #334155;
                border-radius: 8px;
                spacing: 6px;
                padding: 4px;
            }
            QToolButton {
                background: #1f2937;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QToolButton:hover {
                background: #273449;
            }
            QToolButton:pressed {
                background: #334155;
            }
            QToolBar QLineEdit {
                min-height: 26px;
            }
            QCheckBox {
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #334155;
                border-radius: 4px;
                background: #0b1220;
            }
            QCheckBox::indicator:checked {
                background: #2563eb;
                border-color: #2563eb;
            }
            QCheckBox::indicator:unchecked:hover {
                background: #1f2937;
                border-color: #475569;
            }
        """,
    }

    def __init__(self, vm_lang: LanguageViewModel):

        self._initializing = True
        # -----------------------------
        # Language support
        # -----------------------------
        # Store reference to the LanguageViewModel
        self._vm_lang = vm_lang
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
        self._apply_theme()
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
        """Bind ViewModel signals to View updates (model → view)."""
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
        lbl.setAlignment(Qt.AlignLeft)  # type: ignore[attr-defined]
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

        for col in range(columns):
            layout.setColumnStretch(col, 1)  # all columns get equal stretch

        for field in fields:
            if isinstance(field, SectionConfig):
                frame = QFrame()
                frame.setObjectName("card")

                frame_layout = QVBoxLayout(frame)
                label = QLabel()
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

                label = QLabel()
                widget: QWidget = field.widget_type()
                if isinstance(widget, QLineEdit):
                    widget.setValidator(QDoubleValidator())

                layout.addWidget(label, row, col)
                layout.addWidget(widget, row, col + 1)

                self._widgets[field.key] = widget
                self._labels[field.key] = label

        return layout

    @staticmethod
    def cell_has_widget(grid_layout: QGridLayout, row: int, col: int) -> bool:
        item = grid_layout.itemAtPosition(row, col)
        return item is not None and item.widget() is not None

    def _create_page_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        return layout

    def _create_card(self) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 14, 16, 14)
        frame_layout.setSpacing(10)
        return frame, frame_layout

    def _wrap_in_scroll_area(self, content_widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_widget)
        return scroll

    def _apply_theme(self) -> None:
        widget = self if isinstance(self, QWidget) else None
        if widget is None:
            return

        widget.setObjectName("viewRoot")
        theme = BaseView._themes.get(BaseView._active_theme, BaseView._themes["light"])
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
            view._apply_theme()

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
