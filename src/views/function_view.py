from functools import partial

from PySide6.QtCore import QObject, Qt, QT_TRANSLATE_NOOP
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel, QLineEdit, QFrame, QComboBox
from numpy import ndarray

from app_domain.functions import FunctionTypes, resolve_function_type
from utils import LatexRenderer
from viewmodels import LanguageViewModel, FunctionViewModel, PlotViewModel
from views import BaseView, PlotView, PlotConfiguration
from views.translations import ViewTitle


class FunctionView(BaseView, QWidget):
    """View for selecting and configuring functions and displaying the plot."""

    def __init__(
            self,
            vm_lang: LanguageViewModel,
            vm_function: FunctionViewModel,
            vm_plot: PlotViewModel,
            title: ViewTitle,
            show_start_end_time: bool = True,
            parent: QObject | None = None,
    ) -> None:
        QWidget.__init__(self, parent)

        self._vm_function = vm_function
        self._vm_plot = vm_plot

        self._title = title
        self._show_start_end_time = show_start_end_time

        self._txt_function_params: dict[str, QLineEdit] = {}

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""

        main_layout = QVBoxLayout()

        # Title
        self._lbl_title = QLabel()
        self._apply_title_property(self._lbl_title)

        main_layout.addWidget(self._lbl_title)

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)      # type: ignore[attr-defined]

        self._frame_layout = QVBoxLayout()

        self._cmb_function = QComboBox()
        self._frame_layout.addWidget(self._cmb_function)

        self._param_grid = self._init_param_grid()
        self._frame_layout.addLayout(self._param_grid)

        frame.setLayout(self._frame_layout)
        main_layout.addWidget(frame)

        function_type = resolve_function_type(self._vm_function.selected_function)
        title = self._enum_translation(FunctionTypes).get(function_type)

        self._plot_cfg = PlotConfiguration(
            context="ControlEnums",
            title=title,
            x_label=str(QT_TRANSLATE_NOOP("ControlEnums", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("ControlEnums", "Output")),
            show_start_end_time=self._show_start_end_time,
        )

        plot_view = PlotView(
            self._vm_plot,
            self._plot_cfg,
            self._vm_lang,
        )

        main_layout.addWidget(plot_view)
        self.setLayout(main_layout)

    def _init_param_grid(self) -> QGridLayout:
        """Create and populate the parameter grid."""
        self._logger.debug(
            f"Building parameter grid for function: {self._vm_function.selected_function.__class__.__name__}"
        )

        grid = QGridLayout()
        grid.setColumnStretch(0, 1)  # extra space absorbs expansion
        grid.setColumnStretch(5, 1)  # extra space absorbs expansion

        formula = self._vm_function.selected_function.get_formula()

        lbl_formula = QLabel()
        lbl_formula.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
        lbl_formula.setStyleSheet("background: transparent;")
        lbl_formula.setPixmap(LatexRenderer.latex2pixmap(formula, font_size_scale=1.5))
        lbl_formula.setAlignment(Qt.AlignCenter)    # type: ignore[attr-defined]

        grid.addWidget(lbl_formula, 0, 0, 1, 6)

        self._txt_function_params.clear()

        params = self._vm_function.selected_function.get_param()

        for i, (label, value) in enumerate(params.items()):
            row = i // 2 + 1
            col = (i % 2) * 2 + 1

            lbl_param = QLabel()
            lbl_param.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
            lbl_param.setStyleSheet("background: transparent;")
            lbl_param.setPixmap(LatexRenderer.latex2pixmap(f"{label}:"))

            grid.addWidget(lbl_param, row, col)

            txt_param = QLineEdit()
            txt_param.setValidator(QDoubleValidator())
            txt_param.setFixedWidth(80)
            txt_param.setText(f"{value:.3f}")

            self._txt_function_params[label] = txt_param
            grid.addWidget(txt_param, row, col + 1)

        self._logger.debug(f"Parameter grid created with {len(params)} parameters")

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

        # Function ViewModel → View
        self._vm_function.functionChanged.connect(self._on_vm_function_changed)
        self._vm_function.computeFinished.connect(self._on_vm_compute_finished)
        self._vm_function.parameterChanged.connect(self._on_vm_param_changed)

        # Plot ViewModel → Function recomputation
        self._vm_plot.startTimeChanged.connect(self._on_vm_time_changed)
        self._vm_plot.endTimeChanged.connect(self._on_vm_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""

        self._lbl_title.setText(self._enum_translation(ViewTitle).get(self._title))

        function_labels = self._enum_translation(FunctionTypes)
        selected_type = resolve_function_type(self._vm_function.selected_function)

        was_blocked = self._cmb_function.blockSignals(True)
        try:
            self._cmb_add_item(self._cmb_function, function_labels)
            index = self._cmb_function.findData(selected_type)
            if index >= 0:
                self._cmb_function.setCurrentIndex(index)
        finally:
            self._cmb_function.blockSignals(was_blocked)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        selected_type = resolve_function_type(self._vm_function.selected_function)
        index = self._cmb_function.findData(selected_type)
        if index >= 0:
            was_blocked = self._cmb_function.blockSignals(True)
            try:
                self._cmb_function.setCurrentIndex(index)
            finally:
                self._cmb_function.blockSignals(was_blocked)

        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time
        self._vm_function.compute_function(t0, t1)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_function_changed(self) -> None:
        """Rebuild parameter grid when selected function changes."""
        self._logger.info(f"Function changed to: {self._vm_function.selected_function.__class__.__name__}")

        if self._param_grid is not None:
            self._clear_layout(self._param_grid)

        self._param_grid = self._init_param_grid()
        self._frame_layout.addLayout(self._param_grid)

        function_type = resolve_function_type(self._vm_function.selected_function)
        self._plot_cfg.title = self._enum_translation(FunctionTypes).get(function_type)

    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        """Update plot data after function computation completes."""
        self._logger.debug("Function computation finished, updating plot")
        self._vm_plot.update_data("function", (t, y))

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time
        self._logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._vm_function.compute_function(t0, t1)

    def _on_vm_param_changed(self, key: str) -> None:
        """
        Update the QLineEdit text if this parameter changed in ViewModel.
        This prevents feedback loops.
        """
        txt = self._txt_function_params.get(key)
        value = self._vm_function.selected_function.get_param_value(key)
        txt.setText(f"{value:.{self._dec}f}")

        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time
        self._vm_function.compute_function(t0, t1)

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_cmb_func_index_changed(self) -> None:
        """Handle user selection of a different function."""
        if self._initializing:
            return

        selected = self._cmb_function.currentData()
        if selected is None:
            return

        current_type = resolve_function_type(self._vm_function.selected_function)
        if selected == current_type:
            return

        self._logger.info(f"User selected function: {selected.name}")

        self._vm_function.set_selected_function(selected)
        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time
        self._vm_function.compute_function(t0, t1)

    def _on_txt_param_edited(self, key: str) -> None:
        """Read user input and update ViewModel."""
        txt = self._txt_function_params[key]
        text = txt.text().strip()

        try:
            value = float(text)
        except ValueError:
            # Invalid input → restore ViewModel value
            value = self._vm_function.selected_function.get_param_value(key)
            txt.setText(f"{value:.{self._dec}f}")
            return

        self._vm_function.update_param_value(key, value)
