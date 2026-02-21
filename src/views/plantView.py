from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QScrollArea
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression, Qt, QT_TRANSLATE_NOOP

from viewmodels import LanguageViewModel, PlantViewModel, PlotViewModel
from .baseView import BaseView
from .plotView import PlotView, PlotConfiguration
from utils import LatexRenderer

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

        # Scale factor for rendering the LaTeX formula
        self._formula_font_size_scale = 1.5

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """
        Initialize all UI components and layout.
        """

        # Validator: allow only digits, dot, comma and whitespace
        regex = QRegularExpression(r"[0-9.,\s]*")
        validator = QRegularExpressionValidator(regex)

        main_layout = QGridLayout()
        main_layout.setColumnStretch(2, 1)

        # -------------------
        # Numerator input
        # -------------------
        self._lbl_num = QLabel(self.tr("plant.num"))

        self._txt_num = QLineEdit()
        self._txt_num.setValidator(validator)
        self._txt_num.setPlaceholderText("b_n, b_n-1, ..., b_1, b_0")

        # Set fixed width (height follows style automatically)
        self._txt_num.setFixedWidth(220)

        main_layout.addWidget(self._lbl_num, 0, 0)
        main_layout.addWidget(self._txt_num, 0, 1)

        # -------------------
        # Denominator input
        # -------------------
        self._lbl_den = QLabel(self.tr("plant.den"))

        self._txt_den = QLineEdit()
        self._txt_den.setValidator(validator)
        self._txt_den.setPlaceholderText("a_n, a_n-1, ..., a_1, a_0")

        # Same fixed width for visual consistency
        self._txt_den.setFixedWidth(220)

        main_layout.addWidget(self._lbl_den, 1, 0)
        main_layout.addWidget(self._txt_den, 1, 1)

        # -------------------
        # Transfer function formula display
        # -------------------
        self._lbl_formula = QLabel()
        self._lbl_formula.setPixmap(
            LatexRenderer.latex_to_pixmap(
                self._vm_plant.get_formula(),
                font_size_scale=self._formula_font_size_scale,
            )
        )
        self._lbl_formula.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # type: ignore[attr-defined]

        # --- Scroll area for label ---
        scroll_formula = QScrollArea()
        scroll_formula.setWidget(self._lbl_formula)
        scroll_formula.setWidgetResizable(True)
        scroll_formula.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)   # type: ignore[attr-defined]
        scroll_formula.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded) # type: ignore[attr-defined]
        scroll_formula.setFrameShape(QScrollArea.NoFrame)   # type: ignore[attr-defined]

        main_layout.addWidget(scroll_formula, 0, 2, 2, 2)

        # -------------------
        # Step response
        # -------------------
        plot_cfg  = PlotConfiguration(
            context="plant.view",
            title=str(QT_TRANSLATE_NOOP("plant.view", "Step Response")),
            x_label=str(QT_TRANSLATE_NOOP("plant.view", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("plant.view", "Output")),
            figsize=(5, 3)
        )

        self._plot_view = PlotView(self._vm_plot, plot_cfg, self._vm_lang)

        main_layout.addWidget(self._plot_view, 2, 0, 3, 0)

        self.setLayout(main_layout)

    # -------------------------------------------------
    # Signal connections (UI → ViewModel)
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        self._txt_num.textChanged.connect(self._on_txt_num_changed)
        self._txt_den.textChanged.connect(self._on_txt_den_changed)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        self._vm_plant.numChanged.connect(self._on_vm_num_changed)
        self._vm_plant.denChanged.connect(self._on_vm_den_changed)
        self._vm_plant.formulaChanged.connect(self._on_vm_formula_changed)
        self._vm_plant.stepResponseChanged.connect(
            lambda: self._vm_plot.update_data("Step Response", self._vm_plant.get_step_response_result())
        )

    # -------------------------------------------------
    # Retranslation (for language changes)
    # -------------------------------------------------
    def _retranslate(self) -> None:
        self._lbl_num.setText(self.tr("plant.num"))
        self._lbl_den.setText(self.tr("plant.den"))

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_num_changed(self) -> None:
        """
        Update numerator input field when ViewModel changes.
        """
        self._txt_num.setText(self._vm_plant.num)

    def _on_vm_den_changed(self) -> None:
        """
        Update denominator input field when ViewModel changes.
        """
        self._txt_den.setText(self._vm_plant.den)

    def _on_vm_formula_changed(self) -> None:
        """
        Update LaTeX formula label when ViewModel formula changes.
        """
        self._lbl_formula.setPixmap(
            LatexRenderer.latex_to_pixmap(
                self._vm_plant.get_formula(),
                font_size_scale=self._formula_font_size_scale,
            )
        )

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