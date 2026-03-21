from functools import partial
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QComboBox,
    QGridLayout,
    QLineEdit,
    QLayout,
    QHBoxLayout,
    QGraphicsOpacityEffect,
)
from PySide6.QtGui import QDoubleValidator, Qt

from app_domain.ui_context import UiContext
from app_domain.functions import resolve_function_type, FunctionTypes
from viewmodels import FunctionViewModel
from views import ViewMixin
from . import SectionFrame
from .formula_widget import FormulaWidget

FORMULA = "formula"

class FunctionWidget(ViewMixin, QWidget):
    """Widget for selecting a function and editing its parameters."""

    functionChanged = Signal()

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
            self,
            ui_context: UiContext,
            vm_function: FunctionViewModel,
            excluded_function_types: list[FunctionTypes] | None = None,
            parent: QWidget = None
    ):
        QWidget.__init__(self, parent)

        self._vm_function = vm_function

        if excluded_function_types is None:
            excluded_function_types = []
        self._excluded_function_types = excluded_function_types

        self._txt_function_params: dict[str, QLineEdit] = {}
        self._lbl_function_params: dict[str, FormulaWidget] = {}
        self._param_frame_opacity: QGraphicsOpacityEffect | None = None

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        main_layout.addLayout(layout)

        layout.addLayout(self._create_function_selector_layout(), 1)

        self._frm_param = self._create_param_frame()
        layout.addWidget(self._frm_param, 1)
        self._set_param_frame_visible(self._show_formula())

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_function_selector_layout(self) -> QLayout:
        """Create the function selector container layout."""
        layout = self._create_page_layout()

        self._cmb_function = QComboBox(self)
        layout.addWidget(self._cmb_function)

        lbl_formula = FormulaWidget(font_size_scale=self._formula_font_size_scale, parent=self)
        layout.addWidget(lbl_formula, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.field_widgets.setdefault(FORMULA, lbl_formula)

        return layout

    def _create_param_frame(self) -> SectionFrame:
        """Create the parameter widget container layout."""
        frame: SectionFrame
        frame, layout = self._create_card(parent=self)

        grid = self._create_param_grid(frame)
        layout.addLayout(grid)

        return frame

    def _create_param_grid(self, parent: Optional[QWidget] = None) -> QGridLayout:
        """Create and populate the parameter grid."""
        self.logger.debug(
            f"Building parameter grid for function: {self._vm_function.selected_function.__class__.__name__}"
        )

        grid = QGridLayout()

        params = self._vm_function.selected_function.get_param()
        self._lbl_function_params.clear()
        self._txt_function_params.clear()

        row_offset = 0

        for i, (label, value) in enumerate(params.items()):
            row = i // 2 + row_offset
            col = (i % 2) * 2

            lbl_param = FormulaWidget(label + ":", self._formula_font_size_scale, parent=parent)

            self._lbl_function_params.setdefault(label, lbl_param)
            grid.addWidget(lbl_param, row, col, alignment=Qt.AlignmentFlag.AlignRight)

            txt_param = QLineEdit(parent)
            txt_param.setValidator(QDoubleValidator())
            txt_param.setFixedWidth(220)
            txt_param.setText(self._format_value(value))

            self._txt_function_params.setdefault(label, txt_param)
            grid.addWidget(txt_param, row, col + 1, alignment=Qt.AlignmentFlag.AlignLeft)

        self.logger.debug(f"Parameter grid created with {len(params)} parameters")

        self._connect_param_signals()

        return grid

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._cmb_function.currentIndexChanged.connect(self._on_cmb_func_index_changed)

    def _connect_param_signals(self) -> None:
        """
        Connect each QLineEdit to ViewModel parameter updates
        and listen to ViewModel signals to update UI automatically.
        """
        for key, txt in self._txt_function_params.items():
            # Update ViewModel on editing finished
            txt.editingFinished.connect(partial(self._on_txt_param_edited, key))

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_function.functionChanged.connect(self._on_vm_function_changed)
        self._vm_function.parameterChanged.connect(self._on_vm_param_changed)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._frm_param.setText(self.tr("Parameters"))
        function_labels = {
            key: self._enum_translation(key) for key in FunctionTypes
            if key not in self._excluded_function_types
        }

        selected_type = resolve_function_type(self._vm_function.selected_function)
        self._cmb_add_item(self._cmb_function, function_labels)
        index = self._cmb_function.findData(selected_type)
        if index >= 0:
            self._cmb_function.setCurrentIndex(index)

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        selected_type = resolve_function_type(self._vm_function.selected_function)
        index = self._cmb_function.findData(selected_type)
        if index >= 0:
            self._cmb_function.setCurrentIndex(index)

        self._update_formula()
        self._set_param_frame_visible(self._show_formula())

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        for formula, label in self._lbl_function_params.items():
            label.set_formula(f"{formula}:")

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_vm_function_changed(self) -> None:
        """Rebuild parameter grid when selected function changes."""
        self.logger.info(f"Function changed to: {self._vm_function.selected_function.__class__.__name__}")

        if self._cmb_function.currentData() == self._vm_function.selected_function:
            self.logger.debug(
                "Function selection ignored because it matches current ViewModel state (%s).",
                self._vm_function.selected_function
            )
            return

        # update cmb index
        selected_type = resolve_function_type(self._vm_function.selected_function)
        index = self._cmb_function.findData(selected_type)
        if index >= 0:
            self._cmb_function.setCurrentIndex(index)

        self._update_formula()

        self._set_param_frame_visible(self._show_formula())

        if self._frm_param.content_layout() is not None:
            self._frm_param.clear_layout()

        grid = self._create_param_grid()
        self._frm_param.add_layout(grid)

        self.functionChanged.emit()

    def _on_vm_param_changed(self, key: str) -> None:
        """
        Update the QLineEdit text if this parameter changed in ViewModel.
        This prevents feedback loops.
        """
        txt = self._txt_function_params.get(key)
        if txt is None:
            return

        value = self._vm_function.selected_function.get_param_value(key)
        formatted_value = self._format_value(value)

        if txt.text() != formatted_value:
            txt.setText(formatted_value)
            self.functionChanged.emit()

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_cmb_func_index_changed(self) -> None:
        """Handle user selection of a different function."""
        if self.initializing:
            return

        selected = self._cmb_function.currentData()
        if selected is None:
            return

        current_type = resolve_function_type(self._vm_function.selected_function)
        if selected == current_type:
            return

        self.logger.info(f"User selected function: {selected.name}")

        self._vm_function.set_selected_function(selected)

    def _on_txt_param_edited(self, key: str) -> None:
        """Read user input and update ViewModel."""
        txt = self._txt_function_params[key]
        text = txt.text().strip()

        try:
            value = float(text)
        except ValueError:
            # Invalid input -> restore ViewModel value
            value = self._vm_function.selected_function.get_param_value(key)
            txt.setText(self._format_value(value))
            return

        txt.setText(self._format_value(value))
        self._vm_function.update_param_value(key, value)

    # ============================================================
    # UI helpers
    # ============================================================
    def _update_formula(self) -> None:
        widget: FormulaWidget = self.field_widgets.get(FORMULA)

        if self._show_formula():
            formula = self._vm_function.selected_function.get_formula()
            widget.set_formula(formula)

        else:
            widget.clear_formula()

    def _show_formula(self) -> bool:
        return resolve_function_type(self._vm_function.selected_function) != FunctionTypes.NULL

    def _set_param_frame_visible(self, visible: bool) -> None:
        if self._param_frame_opacity is None:
            self._param_frame_opacity = QGraphicsOpacityEffect(self._frm_param)
            self._frm_param.setGraphicsEffect(self._param_frame_opacity)

        self._param_frame_opacity.setOpacity(1.0 if visible else 0.0)
        self._frm_param.setEnabled(visible)
        self._frm_param.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not visible)
