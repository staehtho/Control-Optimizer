from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QTabWidget, QScrollArea
from PySide6.QtCore import Qt

from app_domain.controlsys import ExcitationTarget
from utils import LatexRenderer
from viewmodels import LanguageViewModel, PlantViewModel, EvaluationViewModel, FunctionViewModel, PlotViewModel
from views import BaseView, FunctionView
from views.translations import Translation, ViewTitle


class EvaluationView(BaseView, QWidget):
    def __init__(
            self,
            vm_lang: LanguageViewModel,
            vm_plant: PlantViewModel,
            vm_evaluator: EvaluationViewModel,
            vm_functions: dict[str, FunctionViewModel],
            vm_plots: dict[str, PlotViewModel],
            parent: QWidget = None
    ):
        QWidget.__init__(self, parent)

        self._vm_lang = vm_lang
        self._vm_plant = vm_plant
        self._vm_evaluator = vm_evaluator
        self._vm_functions = vm_functions
        self._vm_plots = vm_plots

        self._function_tab_pages: dict[str, QWidget] = {}

        self._latex_labels: dict[str, QLabel] = {}

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)

        main_layout.addWidget(self._create_cl_frame())
        main_layout.addWidget(self._create_function_frame())

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_widget)

        # Outer layout for your view
        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll)

        self.setLayout(outer_layout)

    def _create_cl_frame(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_cl = QLabel()
        self._apply_title_property(self._lbl_title_cl)
        frame_layout.addWidget(self._lbl_title_cl)

        # TF closed loop
        latex_text = {
            "cl": r"T(s) = C(s) \cdot G(s)",
            "controller": r"C(s) = \frac{K_p}{T_i}",
            "plant": r"G(s) = " + self._vm_plant.get_tf(),
        }

        for key, text in latex_text.items():
            lbl_latex = QLabel()
            lbl_latex.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
            lbl_latex.setStyleSheet("background: transparent;")

            lbl_latex.setPixmap(
                LatexRenderer.latex2pixmap(
                    text,
                    font_size_scale=self._formula_font_size_scale
                )
            )
            lbl_latex.setAlignment(Qt.AlignHCenter)  # type: ignore[attr-defined]

            frame_layout.addWidget(lbl_latex)

            self._latex_labels[key] = lbl_latex

        return frame

    def _create_function_frame(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_function = QLabel()
        self._apply_title_property(self._lbl_title_function)
        frame_layout.addWidget(self._lbl_title_function)

        # Function Tab
        self._function_tab = QTabWidget()
        frame_layout.addWidget(self._function_tab)

        # create function tab pages
        for key in self._vm_functions.keys():
            function_page = QWidget()
            function_page_layout = QVBoxLayout(function_page)
            function_view = FunctionView(self._vm_lang, self._vm_functions[key], self._vm_plots[key], ViewTitle[key])
            function_page_layout.addWidget(function_view)

            self._function_tab_pages.setdefault(key, function_page)
            self._function_tab.addTab(function_page, key)

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        ...

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        ...

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title_cl.setText(self.tr("Closed Loop"))
        self._lbl_title_function.setText(self.tr("Excitation Function"))

        # translate pages
        translation = Translation()
        for text, i in zip(ExcitationTarget, range(self._function_tab.count())):
            new_label = translation(ExcitationTarget).get(text)
            self._function_tab.setTabText(i, new_label)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        ...

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
