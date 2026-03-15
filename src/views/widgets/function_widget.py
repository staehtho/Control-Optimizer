from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QGridLayout, QLineEdit
from PySide6.QtGui import QDoubleValidator

from app_domain.ui_context import UiContext
from app_domain.functions import resolve_function_type, FunctionTypes
from viewmodels import FunctionViewModel
from views import ViewMixin
from .formula_widget import FormulaWidget


class FunctionWidget(ViewMixin, QWidget):
    functionChanged = Signal()

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

        ViewMixin.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        frame = self._create_function_selector_layout()
        main_layout.addWidget(frame)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_function_selector_layout(self) -> QWidget:
        container = QWidget(self)
        frame_layout = QVBoxLayout(container)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(10)

        self._cmb_function = QComboBox(container)
        frame_layout.addWidget(self._cmb_function)

        self._param_widget = QWidget(container)
        show_formula = resolve_function_type(self._vm_function.selected_function) != FunctionTypes.NULL
        self._param_grid = self._create_param_grid(show_formula=show_formula)
        self._param_widget.setLayout(self._param_grid)
        frame_layout.addWidget(self._param_widget)

        self._function_layout = frame_layout
        return container

    def _create_param_grid(self, show_formula: bool = True) -> QGridLayout:
        """Create and populate the parameter grid."""
        self.logger.debug(
            f"Building parameter grid for function: {self._vm_function.selected_function.__class__.__name__}"
        )

        grid = QGridLayout()
        grid.setColumnStretch(0, 1)  # extra space absorbs expansion
        grid.setColumnStretch(5, 1)  # extra space absorbs expansion

        params = self._vm_function.selected_function.get_param()
        self._lbl_function_params.clear()
        self._txt_function_params.clear()

        row_offset = 0
        if show_formula:
            formula = self._vm_function.selected_function.get_formula()

            lbl_formula = FormulaWidget(formula, 1.5, parent=self._param_widget)

            grid.addWidget(lbl_formula, 0, 0, 1, 6)
            row_offset = 1

            self._lbl_function_params.setdefault(formula, lbl_formula)

        for i, (label, value) in enumerate(params.items()):
            row = i // 2 + row_offset
            col = (i % 2) * 2 + 1

            lbl_param = FormulaWidget(f"{label}:", 1.5, parent=self._param_widget)

            self._lbl_function_params.setdefault(label, lbl_param)
            grid.addWidget(lbl_param, row, col)

            txt_param = QLineEdit(self._param_widget)
            txt_param.setValidator(QDoubleValidator())
            txt_param.setFixedWidth(80)
            txt_param.setText(self._format_value(value))

            self._txt_function_params.setdefault(label, txt_param)
            grid.addWidget(txt_param, row, col + 1)

        self.logger.debug(f"Parameter grid created with {len(params)} parameters")

        self._connect_param_signals()

        return grid

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
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

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_function.functionChanged.connect(self._on_vm_function_changed)
        self._vm_function.parameterChanged.connect(self._on_vm_param_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        function_labels = {
            key: self._enum_translation(key) for key in FunctionTypes
            if key not in self._excluded_function_types
        }

        selected_type = resolve_function_type(self._vm_function.selected_function)
        self._cmb_add_item(self._cmb_function, function_labels)
        index = self._cmb_function.findData(selected_type)
        if index >= 0:
            self._cmb_function.setCurrentIndex(index)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        selected_type = resolve_function_type(self._vm_function.selected_function)
        index = self._cmb_function.findData(selected_type)
        if index >= 0:
            self._cmb_function.setCurrentIndex(index)

    # -------------------------------------------------
    # Applied theme
    # -------------------------------------------------
    def _on_theme_applied(self) -> None:
        for formula, label in self._lbl_function_params.items():
            label.set_formula(formula)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
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

        self.setUpdatesEnabled(False)
        try:
            if self._param_grid is not None:
                self._clear_layout(self._param_grid)

            old_param_widget = self._param_widget

            self._param_widget = QWidget(self)
            show_formula = resolve_function_type(self._vm_function.selected_function) != FunctionTypes.NULL
            self._param_grid = self._create_param_grid(show_formula=show_formula)
            self._param_widget.setLayout(self._param_grid)

            self._function_layout.insertWidget(1, self._param_widget)
            self._function_layout.removeWidget(old_param_widget)
            old_param_widget.hide()
            old_param_widget.deleteLater()
        finally:
            self.setUpdatesEnabled(True)
            self.update()

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

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
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
            # Invalid input → restore ViewModel value
            value = self._vm_function.selected_function.get_param_value(key)
            txt.setText(self._format_value(value))
            return

        txt.setText(self._format_value(value))
        self._vm_function.update_param_value(key, value)

