import logging
from PySide6.QtWidgets import QWidget, QLayout, QLabel, QComboBox, QGridLayout, QFrame, QVBoxLayout, QLineEdit
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from dataclasses import dataclass
from typing import Type

from viewmodels import LanguageViewModel


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

    def __init__(self, vm_lang: LanguageViewModel):

        # -----------------------------
        # Language support
        # -----------------------------
        # Store reference to the LanguageViewModel
        self._vm_lang = vm_lang
        # Connect signal: whenever language changes, call _retranslate
        self._vm_lang.languageChanged.connect(self._retranslate)

        # Scale factor for rendering the LaTeX formula
        self._formula_font_size_scale = 1.5
        self._dec = 3
        self._title_size = 16

        self._widgets = {}
        self._labels = {}
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
                    widget.setParent(None)
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def _apply_title_property(self, lbl: QLabel, font_size: int = 0) -> None:
        font = QFont()
        font.setPointSize(self._title_size if font_size == 0 else font_size)  # size in pt
        font.setBold(True)
        lbl.setFont(font)
        lbl.setAlignment(Qt.AlignHCenter)  # type: ignore[attr-defined]

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

        for field in fields:
            if isinstance(field, SectionConfig):
                frame = QFrame()
                frame.setFrameShape(QFrame.StyledPanel)
                frame.setFrameShadow(QFrame.Sunken)

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
                row = 0
                col = 0
                while self.cell_has_widget(layout, row, col):
                    col += 2
                    if col >= columns:
                        col = 0
                        row += 1

                layout.addWidget(frame, row, col, inner_rows, 2)

            else:
                # Normal field
                row = 0
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
