from PySide6.QtCore import QObject
from PySide6.QtCore import QRegularExpression, Qt, QT_TRANSLATE_NOOP
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy
from numpy import ndarray

from app_domain.ui_context import UiContext
from viewmodels import PlantViewModel, PlotViewModel
from viewmodels.types import PlotData
from .base_view import BaseView
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, ExpandableFrame, FormulaWidget
from views.translations import PlotLabels


class PlantView(BaseView, QWidget):

    def __init__(
        self,
            ui_context: UiContext,
        vm_plant: PlantViewModel,
        vm_plot: PlotViewModel,
        parent: QObject = None,
    ):
        QWidget.__init__(self, parent)

        # Reference to the ViewModel
        self._vm_plant = vm_plant
        self._vm_plot = vm_plot

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""

        main_layout = self._create_page_layout()

        # Title
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("viewTitle")
        main_layout.addWidget(self._lbl_title)

        self._frm_tf = self._create_transfer_function_frame()
        main_layout.addWidget(self._frm_tf, 0)
        self._frm_plot = self._create_plot_frame()
        main_layout.addWidget(self._frm_plot, 1)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_transfer_function_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card()
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)
        grid_layout.setColumnStretch(2, 1)

        # Validator: allow only digits, dot, comma, minus and whitespace
        regex = QRegularExpression(r"[0-9.,\-\s]*")
        validator = QRegularExpressionValidator(regex)

        # -------------------
        # Numerator input
        # -------------------
        self._lbl_num = QLabel(self.tr("plant.num"))

        self._txt_num = QLineEdit()
        self._txt_num.setValidator(validator)

        # Set fixed width (height follows style automatically)
        self._txt_num.setFixedWidth(220)

        grid_layout.addWidget(self._lbl_num, 0, 0)
        grid_layout.addWidget(self._txt_num, 0, 1)

        # -------------------
        # Denominator input
        # -------------------
        self._lbl_den = QLabel(self.tr("plant.den"))

        self._txt_den = QLineEdit()
        self._txt_den.setValidator(validator)

        # Same fixed width for visual consistency
        self._txt_den.setFixedWidth(220)

        grid_layout.addWidget(self._lbl_den, 1, 0)
        grid_layout.addWidget(self._txt_den, 1, 1)

        # -------------------
        # Transfer function formula display
        # -------------------
        self._lbl_formula = FormulaWidget(r"G(s) = " + self._vm_plant.get_tf(), self._formula_font_size_scale)

        # --- Scroll area for label ---
        scroll_formula = QScrollArea()
        scroll_formula.setWidget(self._lbl_formula)
        scroll_formula.setWidgetResizable(True)
        scroll_formula.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_formula.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_formula.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_formula.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # cannot be focused at all
        scroll_formula.setStyleSheet("background: transparent;")
        scroll_formula.viewport().setStyleSheet("background: transparent;")

        grid_layout.addWidget(scroll_formula, 0, 2, 4, 1)

        frame_layout.addLayout(grid_layout)

        return frame

    def _create_plot_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card(expand_vertically_when_expanded=True)
        plot_cfg = PlotWidgetConfiguration(
            context="plant.view",
            title=str(QT_TRANSLATE_NOOP("plant.view", "Step Response")),
            x_label=str(QT_TRANSLATE_NOOP("plant.view", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("plant.view", "Output")),
        )

        plot_view = PlotWidget(self._ui_context, self._vm_plot, plot_cfg, parent=self)
        plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        frame_layout.addWidget(plot_view, 1)

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._txt_num.textChanged.connect(self._on_txt_num_changed)
        self._txt_den.textChanged.connect(self._on_txt_den_changed)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # vm plant
        self._vm_plant.numChanged.connect(self._on_vm_num_changed)
        self._vm_plant.denChanged.connect(self._on_vm_den_changed)
        self._vm_plant.tfChanged.connect(self._on_vm_formula_changed)
        self._vm_plant.stepResponseChanged.connect(self._on_step_response_changed)
        # vm plot
        self._vm_plot.xMinChanged.connect(self._on_plot_time_changed)
        self._vm_plot.xMaxChanged.connect(self._on_plot_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Plant"))
        self._frm_tf.set_title(self.tr("Transfer function"))
        self._frm_plot.set_title(self.tr("Step Response"))
        self._lbl_num.setText(self.tr("plant.num"))
        self._lbl_den.setText(self.tr("plant.den"))
        self._txt_num.setPlaceholderText(self.tr("e.g. 1  → 1"))
        self._txt_den.setPlaceholderText(self.tr("e.g. 1, 0, 0  → 1*s^2 + 0*s + 0"))

        tooltip_text = self.tr("tooltip_num_den")
        self._txt_num.setToolTip(tooltip_text)
        self._txt_den.setToolTip(tooltip_text)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        # No initial value to apply
        ...

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_num_changed(self) -> None:
        """Update numerator input field when ViewModel changes."""
        if self._txt_num.text() != self._vm_plant.num:
            self._txt_num.setText(self._vm_plant.num)

    def _on_vm_den_changed(self) -> None:
        """Update denominator input field when ViewModel changes."""
        if self._txt_den.text() != self._vm_plant.den:
            self._txt_den.setText(self._vm_plant.den)

    def _on_vm_formula_changed(self) -> None:
        """Update LaTeX formula label when ViewModel formula changes."""
        self._lbl_formula.set_formula(r"G(s) = " + self._vm_plant.get_tf())

    def _on_plot_time_changed(self) -> None:
        """Update plot when start or end time changes."""
        self._vm_plant.compute_step_response(self._vm_plot.x_min, self._vm_plot.x_max)

    def _on_step_response_changed(self, t: ndarray, y: ndarray) -> None:
        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.PLANT.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.PLANT),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.PLANT),
            )
        )

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_txt_num_changed(self) -> None:
        """Handle user changes in numerator input field."""
        text = self._txt_num.text()
        self._logger.debug(f"UI event: txt_num changed (value={text})")
        self._vm_plant.update_num(text)

    def _on_txt_den_changed(self) -> None:
        """Handle user changes in denominator input field."""
        text = self._txt_den.text()
        self._logger.debug(f"UI event: txt_den changed (value={text})")
        self._vm_plant.update_den(text)
