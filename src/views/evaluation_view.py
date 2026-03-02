from functools import partial

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QTabWidget, QSizePolicy
from PySide6.QtCore import Qt, QT_TRANSLATE_NOOP
from numpy import ndarray

from app_domain.functions import resolve_function_type, FunctionTypes
from app_domain.ui_context import UiContext
from app_domain.controlsys import ExcitationTarget
from utils import LatexRenderer
from viewmodels import PlantViewModel, EvaluationViewModel, FunctionViewModel, PlotViewModel, PlotData
from views import BaseView
from views.widgets import PlotWidget, PlotConfiguration, FunctionWidget

COLORS = {
    "RESPONSE": "#1f77b4",
    "REFERENCE": "#ff7f0e",
    "INPUT_DISTURBANCE": "#2ca02c",
    "MEASUREMENT_DISTURBANCE": "#d62728",
}

PLOT_ORDER = {
    "RESPONSE": 0,
    "REFERENCE": 1,
    "INPUT_DISTURBANCE": 2,
    "MEASUREMENT_DISTURBANCE": 3,
}


class EvaluationView(BaseView, QWidget):
    def __init__(
            self,
            ui_context: UiContext,
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

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""

        main_layout = self._create_page_layout()

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

        self.setLayout(main_layout)

    def _create_cl_frame(self) -> QFrame:
        frame, frame_layout = self._create_card()

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
        frame, frame_layout = self._create_card()

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

            function_widget = FunctionWidget(self._ui_context, self._vm_functions[key], parent=function_page)

            function_page_layout.addWidget(function_widget)
            self._widgets[key] = function_widget

            self._function_tab_pages.setdefault(key, function_page)
            self._function_tab.addTab(function_page, key)

        return frame

    def _create_cl_response_frame(self) -> QFrame:
        frame, frame_layout = self._create_card()

        # Title
        self._lbl_title_cl_response = QLabel()
        self._apply_title_property(self._lbl_title_cl_response)
        frame_layout.addWidget(self._lbl_title_cl_response)

        self._cl_plot_cfg = PlotConfiguration(
            context="EvaluationView",
            title=str(QT_TRANSLATE_NOOP("EvaluationView", "Closed Loop")),
            x_label=str(QT_TRANSLATE_NOOP("EvaluationView", "Time [s]")),
            y_label=str(QT_TRANSLATE_NOOP("EvaluationView", "Output"))
        )

        plot_view = PlotWidget(
            self._ui_context,
            self._vm_plot,
            self._cl_plot_cfg,
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
    # ViewModel bindings (ViewModel -> UI)
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
        self._vm_evaluator.startTimeChanged.connect(self._sync_plot_time_window_from_model)
        self._vm_evaluator.endTimeChanged.connect(self._sync_plot_time_window_from_model)

        # Plot ViewModel -> Function recomputation
        self._vm_plot.startTimeChanged.connect(self._on_vm_time_changed)
        self._vm_plot.endTimeChanged.connect(self._on_vm_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title_cl.setText(self.tr("Closed Loop"))
        self._lbl_title_function.setText(self.tr("Excitation Function"))
        self._lbl_title_cl_response.setText(self.tr("Closed Loop"))

        # translate pages
        for text, i in zip(ExcitationTarget, range(self._function_tab.count())):
            new_label = self._enum_translation(ExcitationTarget).get(text)
            self._function_tab.setTabText(i, new_label)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._sync_plot_time_window_from_model()

        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time

        for vm in self._vm_functions.values():
            vm.refresh_from_model()
            vm.compute_function(t0, t1)

        self._vm_evaluator.compute_closed_loop_response(t0, t1)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_tf_changed(self) -> None:
        label = self._latex_labels.get("plant")
        text = self._vm_plant.get_tf()
        label.setPixmap(LatexRenderer.latex2pixmap(r"G(s) = " + text, font_size_scale=self._formula_font_size_scale))

    def _on_vm_function_compute_finished(self, key: str, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Function VM '%s' finished computation -> updating plot (samples=%d)",
            key, len(t),
        )

        show = True
        if resolve_function_type(self._vm_functions.get(key).selected_function) == FunctionTypes.NULL:
            show = False

        self._vm_plot.update_data(
            PlotData(
                key=key,
                label=self._enum_translation(ExcitationTarget).get(ExcitationTarget[key]),
                x=t,
                y=y,
                color=COLORS.get(key),
                order=PLOT_ORDER.get(key),
                show=show,
            )
        )

    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Closed-loop response computation finished -> updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plot.update_data(
            PlotData("RESPONSE", "RESPONSE", t, y, COLORS.get("RESPONSE"), PLOT_ORDER.get("RESPONSE"))
        )

    def _on_vm_pso_simulation_finished(self, target: ExcitationTarget) -> None:
        self._logger.debug(
            "PSO simulation finished for target '%s' -> refreshing all excitation functions",
            target.name,
        )

        self._sync_plot_time_window_from_model()

        t0 = self._vm_evaluator.start_time
        t1 = self._vm_evaluator.end_time

        self._vm_evaluator.compute_closed_loop_response(t0, t1)

        # update all function plots
        for vm in self._vm_functions.values():
            vm.refresh_from_model()
            vm.compute_function(t0, t1)

        # update tab index
        index = self._function_tab.indexOf(self._function_tab_pages.get(target.name))
        if index >= 0:
            self._function_tab.setCurrentIndex(index)

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time
        self._vm_evaluator.end_time = t1
        self._vm_evaluator.start_time = t0
        t0 = self._vm_evaluator.start_time
        t1 = self._vm_evaluator.end_time
        self._logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._vm_evaluator.compute_closed_loop_response(t0, t1)

        for vm in self._vm_functions.values():
            vm.compute_function(t0, t1)

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_vm_function_changed(self, key: str) -> None:
        t0 = self._vm_plot.start_time
        t1 = self._vm_plot.end_time

        self._logger.debug(
            "Excitation function changed -> recomputing closed-loop response (time window=[%.3f, %.3f])",
            t0, t1,
        )

        self._vm_functions.get(key).compute_function(t0, t1)
        self._vm_evaluator.compute_closed_loop_response(t0, t1)

    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        start_time = self._vm_evaluator.start_time
        end_time = self._vm_evaluator.end_time
        if start_time >= end_time:
            return

        current_start = self._vm_plot.start_time
        current_end = self._vm_plot.end_time

        # Update in a valid order so PlotViewModel constraints are respected.
        if end_time > current_start:
            if current_end != end_time:
                self._vm_plot.end_time = end_time
            if current_start != start_time:
                self._vm_plot.start_time = start_time
        else:
            if current_start != start_time:
                self._vm_plot.start_time = start_time
            if current_end != end_time:
                self._vm_plot.end_time = end_time
