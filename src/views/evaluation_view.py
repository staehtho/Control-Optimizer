from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QTabWidget
from PySide6.QtCore import QT_TRANSLATE_NOOP
from numpy import ndarray

from app_domain.engine.types import FrequencyResponse
from app_domain.ui_context import UiContext
from viewmodels import EvaluationViewModel, PlotViewModel
from viewmodels.types import PlotData, BodePlotData
from views import BaseView
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, SubplotConfiguration, ExpandableFrame, FormulaWidget, BodePlotWidget
from views.translations import PlotLabels


class EvaluationView(BaseView, QWidget):
    def __init__(
            self,
            ui_context: UiContext,
            vm_evaluator: EvaluationViewModel,
            vm_plots: dict[str, PlotViewModel],
            parent: QWidget = None
    ):
        QWidget.__init__(self, parent)

        self._vm_evaluator = vm_evaluator
        self._vm_plots = vm_plots

        self._plot_tab_pages: dict[str, QWidget] = {}

        self._latex_labels: dict[str, QLabel] = {}

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""

        main_layout = self._create_page_layout()

        # Title
        self._lbl_title = QLabel(self)
        self._lbl_title.setObjectName("viewTitle")
        main_layout.addWidget(self._lbl_title)

        self._frm_cl = self._create_cl_frame()
        main_layout.addWidget(self._frm_cl, 0)
        self._frm_plot = self._create_plot_frame()
        main_layout.addWidget(self._frm_plot, 1)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_cl_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card(self)

        # TF closed loop
        latex_text = {
            "cl": r"T(s) = \frac{C(s) \cdot G(s)}{1 + C(s) \cdot G(s)}",
            "controller": r"C(s) = K_p \left( 1 + \frac{1}{T_i\,s} + \frac{T_d\,s}{1 + T_f\,s} \right)",
            "plant": r"G(s) = " + self._vm_evaluator.plant_tf,
        }

        for key, text in latex_text.items():
            lbl_latex = FormulaWidget(text, self._formula_font_size_scale, parent=frame)
            frame_layout.addWidget(lbl_latex)
            self._latex_labels[key] = lbl_latex

        return frame

    def _create_plot_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card(self, True)

        self._plot_tab = QTabWidget(frame)
        frame_layout.addWidget(self._plot_tab)

        widget_time_domain = self._create_time_domain_widget()
        self._plot_tab_pages.setdefault("time_domain", widget_time_domain)
        self._plot_tab.addTab(widget_time_domain, "time_domain")

        widget_frequency_domain = self._create_frequency_domain_widget()
        self._plot_tab_pages.setdefault("frequency_domain", widget_frequency_domain)
        self._plot_tab.addTab(widget_frequency_domain, "frequency_domain")

        return frame

    def _create_time_domain_widget(self) -> QWidget:

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

        widget = PlotWidget(self._ui_context, self._vm_plots.get("time_domain"), cl_plot_cfg, parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        return widget

    def _create_frequency_domain_widget(self) -> QWidget:
        widget = BodePlotWidget(self._ui_context, self._vm_plots.get("frequency_domain"), parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        return widget

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        ...

    # -------------------------------------------------
    # ViewModel bindings (ViewModel -> UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # vm evaluator
        self._vm_evaluator.closedLoopResponseChanged.connect(self._on_vm_closed_loop_compute_finished)
        self._vm_evaluator.plantResponseChanged.connect(self._on_vm_plant_compute_finished)
        self._vm_evaluator.functionChanged.connect(self._on_vm_compute_finished)
        self._vm_evaluator.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)
        self._vm_evaluator.plantFrequencyResponseChanged.connect(self._on_vm_frequency_computation_finished)
        self._vm_evaluator.closedLoopFrequencyResponseChanged.connect(self._on_vm_frequency_computation_finished)

        # Plot ViewModel -> Function recomputation
        self._vm_plots.get("time_domain").xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plots.get("time_domain").xMaxChanged.connect(self._on_vm_time_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Evaluation"))
        self._frm_cl.set_title(self.tr("Closed Loop"))
        self._frm_plot.set_title(self.tr("Closed Loop"))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._sync_plot_time_window_from_model()

        self._update_time_domain_plots()
        self._update_frequency_domain_plots()

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Function finished computation -> updating plot (samples=%d)",
            len(t),
        )

        key = self._vm_evaluator.excitation_target.name

        self._vm_plots.get("time_domain").update_data(
            PlotData(
                key=PlotLabels[key].value,
                label=self._enum_translation(PlotLabels).get(PlotLabels[key]),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels[key]),
                subplot_position=1,
            )
        )

    def _on_vm_closed_loop_compute_finished(self, t: ndarray, u: ndarray, y: ndarray) -> None:
        self._logger.debug(
            "Closed-loop response computation finished -> updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plots.get("time_domain").update_data(
            PlotData(
                key=PlotLabels.CLOSED_LOOP.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.CLOSED_LOOP),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.CLOSED_LOOP),
                subplot_position=1,
            )
        )

        self._vm_plots.get("time_domain").update_data(
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
        self._vm_plots.get("time_domain").update_data(
            PlotData(
                key=PlotLabels.PLANT.value,
                label=self._enum_translation(PlotLabels).get(PlotLabels.PLANT),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.PLANT),
                subplot_position=1,
            )
        )

    def _on_vm_frequency_computation_finished(self, result: FrequencyResponse) -> None:
        self._logger.debug(
            "Closed loop frequency response computation finished -> updating response plot (samples=%d)",
            len(result.omega)
        )

        keys = set(result.margin.keys()) | set(result.phase.keys())

        for key in keys:
            self._vm_plots.get("frequency_domain").update_data(
                BodePlotData(
                    key=PlotLabels[key].value,
                    label=self._enum_translation(PlotLabels).get(PlotLabels[key]),
                    omega=result.omega,
                    margin=result.margin.get(key),
                    phase=result.phase.get(key),
                    plot_style=PLOT_STYLE.get(PlotLabels[key]),
                )
            )

    def _on_vm_pso_simulation_finished(self) -> None:
        self._logger.debug(
            "PSO simulation finished -> refreshing excitation function"
        )

        self._sync_plot_time_window_from_model()

        self._update_time_domain_plots()
        self._update_frequency_domain_plots()

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plots.get("time_domain").x_min
        t1 = self._vm_plots.get("time_domain").x_max

        self._logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._update_time_domain_plots()

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        self._vm_plots.get("time_domain").x_min = self._vm_evaluator.t0
        self._vm_plots.get("time_domain").x_max = self._vm_evaluator.t1

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def _update_time_domain_plots(self) -> None:
        t0 = self._vm_plots.get("time_domain").x_min
        t1 = self._vm_plots.get("time_domain").x_max

        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)
        self._vm_evaluator.compute_function(t0, t1)

    def _update_frequency_domain_plots(self) -> None:
        omega_min = self._vm_plots.get("frequency_domain").x_min
        omega_max = self._vm_plots.get("frequency_domain").x_max

        self._vm_evaluator.compute_plant_frequency_response(omega_min, omega_max)
        self._vm_evaluator.compute_closed_loop_frequency_response(omega_max, omega_min)
