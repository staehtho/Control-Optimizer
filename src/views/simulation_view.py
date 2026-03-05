from functools import partial

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget, QSizePolicy
from PySide6.QtCore import QT_TRANSLATE_NOOP
from numpy import ndarray

from app_domain.functions import resolve_function_type, FunctionTypes
from app_domain.ui_context import UiContext
from app_domain.controlsys import ExcitationTarget
from viewmodels import FunctionViewModel, PlotViewModel, SimulationViewModel
from viewmodels.types import PlotData
from views import BaseView
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, SubplotConfiguration, ExpandableFrame, FunctionWidget
from views.translations import PlotLabels


class SimulationView(BaseView, QWidget):
    def __init__(
            self,
            ui_context: UiContext,
            vm_simulation: SimulationViewModel,
            vm_functions: dict[str, FunctionViewModel],
            vm_plot: PlotViewModel,
            parent: QWidget = None
    ):
        QWidget.__init__(self, parent)

        self._vm_simulation = vm_simulation
        self._vm_functions = vm_functions
        self._vm_plot = vm_plot

        self._function_tab_pages: dict[str, QWidget] = {}

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

        self._frm_function = self._create_function_frame()
        main_layout.addWidget(self._frm_function, 0)
        self._frm_response = self._create_cl_response_frame()
        main_layout.addWidget(self._frm_response, 1)

        main_layout.addStretch()
        self.setLayout(main_layout)

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
                x_label=str(QT_TRANSLATE_NOOP("SimulationView", "Time [s]")),
                y_label=str(QT_TRANSLATE_NOOP("SimulationView", "Output")),
                position=1
            ),
            2: SubplotConfiguration(
                x_label=str(QT_TRANSLATE_NOOP("SimulationView", "Time [s]")),
                y_label=str(QT_TRANSLATE_NOOP("SimulationView", "Output")),
                position=2
            ),
        }

        cl_plot_cfg = PlotWidgetConfiguration(
            context="SimulationView",
            title=str(QT_TRANSLATE_NOOP("SimulationView", "Closed Loop")),
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
        # Function ViewModel
        for key, vm in self._vm_functions.items():
            vm.computeFinished.connect(partial(self._on_vm_function_compute_finished, key))

        # Simulation ViewModel
        self._vm_simulation.closedLoopResponseChanged.connect(self._on_vm_closed_loop_compute_finished)
        self._vm_simulation.plantResponseChanged.connect(self._on_vm_plant_compute_finished)
        self._vm_simulation.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)

        # Plot ViewModel -> Function recomputation
        self._vm_plot.xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plot.xMaxChanged.connect(self._on_vm_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Simulation"))
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
        self._on_vm_pso_simulation_finished()

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
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
                plot_style=PLOT_STYLE.get(PlotLabels[key]),
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
                plot_style=PLOT_STYLE.get(PlotLabels.CLOSED_LOOP),
                subplot_position=1,
            )
        )

        self._vm_plot.update_data(
            PlotData(
                key=PlotLabels.CONTROL_SIGNAL.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.CONTROL_SIGNAL),
                x=t,
                y=u,
                plot_style=PLOT_STYLE.get(PlotLabels.CONTROL_SIGNAL),
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
                plot_style=PLOT_STYLE.get(PlotLabels.PLANT),
                subplot_position=1,
            )
        )

    def _on_vm_pso_simulation_finished(self) -> None:
        target = self._vm_simulation.excitation_target
        self._logger.debug(
            "PSO simulation finished for target '%s' -> refreshing all excitation functions",
            target.name,
        )

        self._sync_plot_time_window_from_model()

        t0 = self._vm_plot.x_min
        t1 = self._vm_plot.x_max

        self._vm_simulation.compute_closed_loop_response(t0, t1)
        self._vm_simulation.compute_plant_response(t0, t1)

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
        self._vm_simulation.compute_closed_loop_response(t0, t1)
        self._vm_simulation.compute_plant_response(t0, t1)

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
        self._vm_simulation.compute_closed_loop_response(t0, t1)
        self._vm_simulation.compute_plant_response(t0, t1)

    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        self._vm_plot.x_min = self._vm_simulation.t0
        self._vm_plot.x_max = self._vm_simulation.t1

