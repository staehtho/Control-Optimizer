from functools import partial

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget, QSizePolicy
from PySide6.QtCore import QT_TRANSLATE_NOOP
from numpy import ndarray

from app_domain.functions import resolve_function_type, FunctionTypes
from app_domain.ui_context import UiContext
from app_domain.controlsys import ExcitationTarget
from utils import LatexRenderer
from viewmodels import PlantViewModel, EvaluationViewModel, FunctionViewModel, PlotViewModel, PlotData
from views import BaseView
from views.widgets import PlotWidget, PlotWidgetConfiguration, SubplotConfiguration, ExpandableFrame, FunctionWidget, \
    FormulaWidget
from views.translations import PlotLabels

COLORS = {
    PlotLabels.REFERENCE: "#ff7f0e",  # orange – reference / setpoint
    PlotLabels.INPUT_DISTURBANCE: "#2ca02c",  # green – input disturbance
    PlotLabels.MEASUREMENT_DISTURBANCE: "#d62728",  # red – measurement disturbance
    PlotLabels.PLANT: "#7f7f7f",  # gray – plant (neutral)
    PlotLabels.CLOSED_LOOP: "#1f77b4",  # blue – closed-loop output
    PlotLabels.CONTROL_SIGNAL: "#9467bd",  # purple – control effort
}

PLOT_ORDER = {
    PlotLabels.REFERENCE: 11,
    PlotLabels.INPUT_DISTURBANCE: 12,
    PlotLabels.MEASUREMENT_DISTURBANCE: 13,
    PlotLabels.PLANT: 14,
    PlotLabels.CLOSED_LOOP: 15,
    PlotLabels.CONTROL_SIGNAL: 10
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

        # Title
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("viewTitle")
        main_layout.addWidget(self._lbl_title)

        self._frm_cl = self._create_cl_frame()
        main_layout.addWidget(self._frm_cl, 0)
        self._frm_function = self._create_function_frame()
        main_layout.addWidget(self._frm_function, 0)
        self._frm_response = self._create_cl_response_frame()
        main_layout.addWidget(self._frm_response, 1)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_cl_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card()

        # TF closed loop
        latex_text = {
            "cl": r"T(s) = \frac{C(s) \cdot G(s)}{1 + C(s) \cdot G(s)}",
            "controller": r"C(s) = K_p \left( 1 + \frac{1}{T_i\,s} + \frac{T_d\,s}{1 + T_f\,s} \right)",
            "plant": r"G(s) = " + self._vm_plant.get_tf(),
        }

        for key, text in latex_text.items():
            lbl_latex = FormulaWidget(text, self._formula_font_size_scale)
            frame_layout.addWidget(lbl_latex)
            self._latex_labels[key] = lbl_latex

        return frame

    def _create_function_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card()

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

    def _create_cl_response_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card(expand_vertically_when_expanded=True)

        subplot_cfgs = {
            1: SubplotConfiguration(
                x_label=str(QT_TRANSLATE_NOOP("EvaluationView", "Time [s]")),
                y_label=str(QT_TRANSLATE_NOOP("EvaluationView", "Output")),
                position=1
            ),
            2: SubplotConfiguration(
                x_label=str(QT_TRANSLATE_NOOP("EvaluationView", "Time [s]")),
                y_label=str(QT_TRANSLATE_NOOP("EvaluationView", "Output")),
                position=2
            ),
        }

        cl_plot_cfg = PlotWidgetConfiguration(
            context="EvaluationView",
            title=str(QT_TRANSLATE_NOOP("EvaluationView", "Closed Loop")),
            subplot=(2, 1),
            subplot_configuration=subplot_cfgs,
        )

        plot_view = PlotWidget(self._ui_context, self._vm_plot, cl_plot_cfg, parent=frame)
        plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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
        self._vm_evaluator.closedLoopResponseChanged.connect(self._on_vm_closed_loop_compute_finished)
        self._vm_evaluator.plantResponseChanged.connect(self._on_vm_plant_compute_finished)
        self._vm_evaluator.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)
        self._vm_evaluator.t0Changed.connect(self._sync_plot_time_window_from_model)
        self._vm_evaluator.t1Changed.connect(self._sync_plot_time_window_from_model)

        # Plot ViewModel -> Function recomputation
        self._vm_plot.xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plot.xMaxChanged.connect(self._on_vm_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Evaluation"))
        self._frm_cl.set_title(self.tr("Closed Loop"))
        self._frm_function.set_title(self.tr("Excitation Function"))
        self._frm_response.set_title(self.tr("Closed Loop"))

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

        t0 = 0
        t1 = self._vm_plot.x_max

        for vm in self._vm_functions.values():
            vm.refresh_from_model()
            vm.compute_function(t0, t1)

        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)

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

        ignore = False
        if resolve_function_type(self._vm_functions.get(key).selected_function) == FunctionTypes.NULL:
            ignore = True

        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels[key].value,
                label=self._enum_translation(PlotLabels).get(PlotLabels[key]),
                x=t,
                y=y,
                color=COLORS.get(PlotLabels[key]),
                order=PLOT_ORDER.get(PlotLabels[key]),
                subplot_position=1,
                ignore_plot=ignore
            )
        )

    def _on_vm_closed_loop_compute_finished(self, t: ndarray, u: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Closed-loop response computation finished -> updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.CLOSED_LOOP.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.CLOSED_LOOP),
                x=t,
                y=y,
                color=COLORS.get(PlotLabels.CLOSED_LOOP),
                order=PLOT_ORDER.get(PlotLabels.CLOSED_LOOP),
                subplot_position=1,
            )
        )

        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.CONTROL_SIGNAL.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.CONTROL_SIGNAL),
                x=t,
                y=u,
                color=COLORS.get(PlotLabels.CONTROL_SIGNAL),
                order=PLOT_ORDER.get(PlotLabels.CONTROL_SIGNAL),
                subplot_position=2,
            )
        )

    def _on_vm_plant_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Plant response computation finished -> updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.PLANT.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.PLANT),
                x=t,
                y=y,
                color=COLORS.get(PlotLabels.PLANT),
                order=PLOT_ORDER.get(PlotLabels.PLANT),
                subplot_position=1,
            )
        )

    def _on_vm_pso_simulation_finished(self, target: ExcitationTarget) -> None:
        self._logger.debug(
            "PSO simulation finished for target '%s' -> refreshing all excitation functions",
            target.name,
        )

        self._sync_plot_time_window_from_model()

        t0 = self._vm_evaluator.t0
        t1 = self._vm_evaluator.t1

        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)

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
        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max

        self._logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)

        for vm in self._vm_functions.values():
            vm.compute_function(t0, t1)

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_vm_function_changed(self, key: str) -> None:
        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max

        self._logger.debug(
            "Excitation function changed -> recomputing closed-loop response (time window=[%.3f, %.3f])",
            t0, t1,
        )

        self._vm_functions.get(key).compute_function(t0, t1)
        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)

    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        self._vm_plot.x_min = self._vm_evaluator.t0
        self._vm_plot.x_max = self._vm_evaluator.t1
