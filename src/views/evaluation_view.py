from functools import partial

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QTabWidget, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, QT_TRANSLATE_NOOP
from numpy import ndarray

from app_domain.controlsys import ExcitationTarget
from utils import LatexRenderer
from viewmodels import LanguageViewModel, PlantViewModel, EvaluationViewModel, FunctionViewModel, PlotViewModel
from views import BaseView
from views.widgets import PlotWidget, PlotConfiguration, FunctionWidget
from views.translations import ViewTitle


class EvaluationView(BaseView, QWidget):
    def __init__(
            self,
            vm_lang: LanguageViewModel,
            vm_plant: PlantViewModel,
            vm_evaluator: EvaluationViewModel,
            vm_functions: dict[str, FunctionViewModel],
            vm_plot: PlotViewModel,
            parent: QWidget = None
    ):
        QWidget.__init__(self, parent)

        self._vm_plant = vm_plant
        self._vm_evaluator = vm_evaluator
        self._vm_functions = vm_functions
        self._vm_plot = vm_plot

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

        cl_frame = self._create_cl_frame()
        function_frame = self._create_function_frame()
        response_frame = self._create_cl_response_frame()

        # Keep the first two frames at their natural height.
        cl_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)  # type: ignore[attr-defined]
        function_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)  # type: ignore[attr-defined]

        # Only the response frame should consume extra vertical space.
        response_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)  # type: ignore[attr-defined]

        main_layout.addWidget(cl_frame, 0)
        main_layout.addWidget(function_frame, 0)
        main_layout.addWidget(response_frame, 1)

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
            "cl": r"T(s) = \frac{C(s) \cdot G(s)}{1 + C(s) \cdot G(s)}",
            "controller": r"C(s) = K_p \left( 1 + \frac{1}{T_i\,s} + \frac{T_d\,s}{1 + T_f\,s} \right)",
            "plant": r"G(s) = " + self._vm_plant.get_tf(),
        }

        for key, text in latex_text.items():
            lbl_latex = QLabel()
            lbl_latex.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
            lbl_latex.setStyleSheet("background: transparent;")

            lbl_latex.setPixmap(LatexRenderer.latex2pixmap(text, font_size_scale=self._formula_font_size_scale))
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

            function_widget = FunctionWidget(self._vm_lang, self._vm_functions[key], parent=function_page)

            function_page_layout.addWidget(function_widget)
            self._widgets[key] = function_widget

            self._function_tab_pages.setdefault(key, function_page)
            self._function_tab.addTab(function_page, key)

        return frame

    def _create_cl_response_frame(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_cl_response = QLabel()
        self._apply_title_property(self._lbl_title_cl_response)
        frame_layout.addWidget(self._lbl_title_cl_response)

        self._cl_plot_cfg = PlotConfiguration(
            context="ControlEnums",
            title=self._enum_translation(ViewTitle).get(ViewTitle.CLOSED_LOOP),
            x_label=str(QT_TRANSLATE_NOOP("ControlEnums", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("ControlEnums", "Output"))
        )

        plot_view = PlotWidget(
            self._vm_plot,
            self._cl_plot_cfg,
            self._vm_lang,
            parent=frame
        )

        frame_layout.addWidget(plot_view)

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        for key, widget in self._widgets.items():
            if isinstance(widget, FunctionWidget):
                widget.functionChanged.connect(partial(self._on_vm_function_changed, key))

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # vm plant
        self._vm_plant.tfChanged.connect(self._on_vm_tf_changed)
        # vm function
        for key, vm in self._vm_functions.items():
            vm.computeFinished.connect(partial(self._on_vm_function_compute_finished, key))
        # vm evaluator
        self._vm_evaluator.closedLoopResponseChanged.connect(self._on_vm_compute_finished)
        self._vm_evaluator.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title_cl.setText(self.tr("Closed Loop"))
        self._lbl_title_function.setText(self.tr("Excitation Function"))
        self._lbl_title_cl_response.setText(self._enum_translation(ViewTitle).get(ViewTitle.CLOSED_LOOP))

        # translate pages
        for text, i in zip(ExcitationTarget, range(self._function_tab.count())):
            new_label = self._enum_translation(ExcitationTarget).get(text)
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
    def _on_vm_tf_changed(self) -> None:
        label = self._latex_labels.get("plant")
        text = self._vm_plant.get_tf()
        label.setPixmap(LatexRenderer.latex2pixmap(r"G(s) = " + text, font_size_scale=self._formula_font_size_scale))

    def _on_vm_function_compute_finished(self, key: str, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Function VM '%s' finished computation → updating plot (samples=%d)",
            key, len(t),
        )
        self._vm_plot.update_data(key, (t, y))

    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Closed-loop response computation finished → updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plot.update_data("response", (t, y))

    def _on_vm_pso_simulation_finished(self, target: ExcitationTarget) -> None:
        self._logger.debug(
            "PSO simulation finished for target '%s' → refreshing all excitation functions",
            target.name,
        )

        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time

        # update all function plots
        for vm in self._vm_functions.values():
            vm.refresh_from_model()
            vm.compute_function(t0, t1)

        # update tab index
        index = self._function_tab.indexOf(self._function_tab_pages.get(target.name))
        if index >= 0:
            self._function_tab.setCurrentIndex(index)

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_vm_function_changed(self, key: str) -> None:
        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time

        self._logger.debug(
            "Excitation function changed → recomputing closed-loop response (time window=[%.3f, %.3f])",
            t0, t1,
        )

        self._vm_functions.get(key).compute_function(t0, t1)
        self._vm_evaluator.compute_closed_loop_response(t0, t1)
