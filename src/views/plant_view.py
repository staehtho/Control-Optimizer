from PySide6.QtCore import QObject
from PySide6.QtCore import QRegularExpression, Qt, QT_TRANSLATE_NOOP
from PySide6.QtGui import QRegularExpressionValidator, QFont
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QScrollArea, QFrame, QVBoxLayout
from numpy import ndarray

from utils import LatexRenderer
from viewmodels import LanguageViewModel, PlantViewModel, PlotViewModel
from .base_view import BaseView
from .plot_view import PlotView, PlotConfiguration


class PlantView(BaseView, QWidget):

    def __init__(
        self,
        vm_lang: LanguageViewModel,
        vm_plant: PlantViewModel,
        vm_plot: PlotViewModel,
        parent: QObject = None,
    ):
        QWidget.__init__(self, parent)

        # Reference to the ViewModel
        self._vm_plant = vm_plant
        self._vm_plot = vm_plot

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""

        # Validator: allow only digits, dot, comma, minus and whitespace
        regex = QRegularExpression(r"[0-9.,\-\s]*")
        validator = QRegularExpressionValidator(regex)

        main_layout = QVBoxLayout()

        # -------------------------------
        # Title
        # -------------------------------
        self._lbl_title = QLabel()
        font = QFont()
        font.setPointSize(self._title_size)  # size in pt
        font.setBold(True)
        self._lbl_title.setFont(font)
        self._lbl_title.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        main_layout.addWidget(self._lbl_title)

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel) # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised) # type: ignore[attr-defined]

        frame_layout = QGridLayout()
        frame_layout.setColumnStretch(2, 1)

        # -------------------
        # Numerator input
        # -------------------
        self._lbl_num = QLabel(self.tr("plant.num"))

        self._txt_num = QLineEdit()
        self._txt_num.setValidator(validator)

        # Set fixed width (height follows style automatically)
        self._txt_num.setFixedWidth(220)

        frame_layout.addWidget(self._lbl_num, 0, 0)
        frame_layout.addWidget(self._txt_num, 0, 1)

        # -------------------
        # Denominator input
        # -------------------
        self._lbl_den = QLabel(self.tr("plant.den"))

        self._txt_den = QLineEdit()
        self._txt_den.setValidator(validator)

        # Same fixed width for visual consistency
        self._txt_den.setFixedWidth(220)

        frame_layout.addWidget(self._lbl_den, 1, 0)
        frame_layout.addWidget(self._txt_den, 1, 1)

        # -------------------
        # Transfer function formula display
        # -------------------
        self._lbl_formula = QLabel()
        self._lbl_formula.setAttribute(Qt.WA_TranslucentBackground) # type: ignore[attr-defined]
        self._lbl_formula.setStyleSheet("background: transparent;")

        self._lbl_formula.setPixmap(
            LatexRenderer.latex2pixmap(
                r"G(s) = " + self._vm_plant.get_tf(),
                font_size_scale=self._formula_font_size_scale
            )
        )
        self._lbl_formula.setAlignment(Qt.AlignVCenter)  # type: ignore[attr-defined]

        # --- Scroll area for label ---
        scroll_formula = QScrollArea()
        scroll_formula.setWidget(self._lbl_formula)
        scroll_formula.setWidgetResizable(True)
        scroll_formula.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)   # type: ignore[attr-defined]
        scroll_formula.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # type: ignore[attr-defined]
        scroll_formula.setFrameShape(QScrollArea.NoFrame)   # type: ignore[attr-defined]
        scroll_formula.setFocusPolicy(Qt.NoFocus)   # type: ignore[attr-defined]  # cannot be focused at all
        scroll_formula.setStyleSheet("background: transparent;")
        scroll_formula.viewport().setStyleSheet("background: transparent;")

        frame_layout.addWidget(scroll_formula, 0, 2, 4, 1)

        frame.setLayout(frame_layout)
        main_layout.addWidget(frame)

        # -------------------
        # Step response
        # -------------------
        plot_cfg  = PlotConfiguration(
            context="plant.view",
            title=str(QT_TRANSLATE_NOOP("plant.view", "Step Response")),
            x_label=str(QT_TRANSLATE_NOOP("plant.view", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("plant.view", "Output")),
        )

        self._plot_view = PlotView(self._vm_plot, plot_cfg, self._vm_lang)

        main_layout.addWidget(self._plot_view)

        self.setLayout(main_layout)

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
        self._vm_plot.startTimeChanged.connect(self._on_plot_time_changed)
        self._vm_plot.endTimeChanged.connect(self._on_plot_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Plant"))
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
        """
        Update numerator input field when ViewModel changes.
        """
        if self._txt_num.text() != self._vm_plant.num:
            self._txt_num.setText(self._vm_plant.num)

    def _on_vm_den_changed(self) -> None:
        """
        Update denominator input field when ViewModel changes.
        """
        if self._txt_den.text() != self._vm_plant.den:
            self._txt_den.setText(self._vm_plant.den)

    def _on_vm_formula_changed(self) -> None:
        """
        Update LaTeX formula label when ViewModel formula changes.
        """
        self._lbl_formula.setPixmap(
            LatexRenderer.latex2pixmap(
                r"G(s) = " + self._vm_plant.get_tf(),
                font_size_scale=self._formula_font_size_scale
            )
        )

    def _on_plot_time_changed(self) -> None:
        """
        Update plot when start or end time changes.
        """
        self._vm_plant.compute_step_response(self._vm_plot.start_time, self._vm_plot.end_time)

    def _on_step_response_changed(self, t: ndarray, y: ndarray) -> None:
        self._vm_plot.update_data("Step Response", (t, y))

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_txt_num_changed(self) -> None:
        """
        Handle user changes in numerator input field.
        """
        text = self._txt_num.text()
        self._logger.debug("UI event: txt_num changed (value=%s)", text)
        self._vm_plant.update_num(text)

    def _on_txt_den_changed(self) -> None:
        """
        Handle user changes in denominator input field.
        """
        text = self._txt_den.text()
        self._logger.debug("UI event: txt_den changed (value=%s)", text)
        self._vm_plant.update_den(text)