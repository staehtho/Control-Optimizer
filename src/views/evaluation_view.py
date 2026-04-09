from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QTabWidget, QHBoxLayout
from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from numpy import ndarray

from app_types import (
    EvaluationField, SectionConfig, FieldConfig, PlotData, BodePlotData, PlotLabels, PsoResultField
)
from resources.blockdiagram import load_closed_loop_diagram
from utils import save_svg
from views import ViewMixin
from views.plot_style import PLOT_STYLE
from views.widgets import (
    PlotWidget, PlotWidgetConfiguration, SubplotConfiguration, BodePlotWidget, AspectRatioSvgWidget, FormulaWidget
)
from resources.resources import Icons

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from app_types import FrequencyResponse
    from viewmodels import EvaluationViewModel, PlotViewModel
    from views.widgets import SectionFrame

TIME_DOMAIN = "time_domain"
FREQUENCY_DOMAIN = "frequency_domain"
TRANSFER_FUNCTION = "transfer_function"
BLOCK_DIAGRAM = "block_diagram"

type PsoFieldText = tuple[dict[str, Any], bool]

FIELDS: dict[str, list[SectionConfig | FieldConfig]] = {
    "tf": [
        SectionConfig(EvaluationField.PLANT, [
            FieldConfig(EvaluationField.TF_PLANT, FormulaWidget, create_label=False),
        ]),
        SectionConfig(EvaluationField.CONTROLLER, [
            FieldConfig(EvaluationField.TF_CONTROLLER, FormulaWidget, create_label=False),
        ]),
        SectionConfig(EvaluationField.OPEN_LOOP, [
            FieldConfig(EvaluationField.TF_OPEN_LOOP, FormulaWidget, create_label=False),
        ]),
        SectionConfig(EvaluationField.CLOSED_LOOP, [
            FieldConfig(EvaluationField.TF_CLOSED_LOOP, FormulaWidget, create_label=False),
        ]),
        SectionConfig(EvaluationField.SENSITIVITY, [
            FieldConfig(EvaluationField.TF_SENSITIVITY, FormulaWidget, create_label=False),
        ]),
    ],
    "result": [
        SectionConfig(PsoResultField.RUN_TIME, [
            FieldConfig(PsoResultField.TIME, QLabel, False)
        ]),
        SectionConfig(PsoResultField.PERFORMANCE_INDEX, [
            SectionConfig(PsoResultField.TIME_DOMAIN, [
                FieldConfig(PsoResultField.ERROR_CRITERION, QLabel, False),
                FieldConfig(PsoResultField.OVERSHOOT_CONTROL, QLabel, False),
                FieldConfig(PsoResultField.SLEW_RATE, QLabel, False),
            ]),
            SectionConfig(PsoResultField.FREQUENCY_DOMAIN, [
                FieldConfig(PsoResultField.GAIN_MARGIN, QLabel, False),
                FieldConfig(PsoResultField.PHASE_MARGIN, QLabel, False),
                FieldConfig(PsoResultField.STABILITY_MARGIN, QLabel, False),
            ])
        ]),
        SectionConfig(PsoResultField.CONTROLLER_PARAMETERS, [
            FieldConfig(PsoResultField.KP, QLabel, False),
            FieldConfig(PsoResultField.TI, QLabel, False),
            FieldConfig(PsoResultField.TD, QLabel, False),
            SectionConfig(PsoResultField.FILTER_TIME_CONSTANT, [
                FieldConfig(PsoResultField.TF, QLabel, False),
                FieldConfig(PsoResultField.TF_LIMITED, QLabel, False),
                FieldConfig(PsoResultField.MIN_SAMPLING_RATE, QLabel, False),
            ]),
        ]),
    ]
}

PSO_RESULT_TEMPLATE: dict[PsoResultField, Any] = {
    PsoResultField.TIME: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "PSO finished after %(time).3f s."
    ),

    PsoResultField.ERROR_CRITERION: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "%(error_criterion)s = %(value).3f"
    ),

    PsoResultField.OVERSHOOT_CONTROL: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Overshoot: %(value).3f %%"
    ),

    PsoResultField.SLEW_RATE: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Slew rate: %(value).3f"
    ),

    PsoResultField.GAIN_MARGIN: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Gain margin: %(value).3f dB @ %(omega).3f rad/s"
    ),

    PsoResultField.PHASE_MARGIN: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Phase margin: %(value).3f° @ %(omega).3f rad/s"
    ),

    PsoResultField.STABILITY_MARGIN: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Stability margin: %(value).3f dB"
    ),

    PsoResultField.KP: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Kp: %(kp).3f"
    ),

    PsoResultField.TI: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Ti: %(ti).3f"
    ),

    PsoResultField.TD: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Td: %(td).3f"
    ),

    PsoResultField.TF: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Tf: %(tf).3f"
    ),

    PsoResultField.TF_LIMITED: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Tf limited by %(limited)s"
    ),

    PsoResultField.MIN_SAMPLING_RATE: QT_TRANSLATE_NOOP(
        "EvaluationView",
        "Min. sampling rate: %(sampling_rate).3f Hz"
    ),
}

LIMITED_TEMPLATE: dict[str, Any] = {
    "simulation": QT_TRANSLATE_NOOP("EvaluationView", "simulation"),
    "sampling": QT_TRANSLATE_NOOP("EvaluationView", "sampling rate"),
}


class EvaluationView(ViewMixin, QWidget):
    """View for evaluating control performance and visualizing results."""

    # ============================================================
    # Initialization
    # ============================================================

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

        self._latex_labels: dict[str, QLabel] = {}

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""

        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.evaluation, self._title_icon_size)
        self._label_icon = QLabel(self)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))
        self._label_icon.setFixedSize(self._title_icon_size, self._title_icon_size)

        self._lbl_title = QLabel(self)
        self._lbl_title.setObjectName("viewTitle")

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)
        title_layout.addWidget(self._label_icon)
        title_layout.addWidget(self._lbl_title)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        self._frm_result = self._create_result_frame()
        main_layout.addWidget(self._frm_result, 0)

        self._frm_plot = self._create_plot_frame()
        main_layout.addWidget(self._frm_plot, 1)

        main_layout.addStretch()
        main_layout.addLayout(self._create_navigation_buttons_layout(parent=self))
        self.setLayout(main_layout)

    def _create_result_frame(self) -> SectionFrame:
        """Create the PSO result summary card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        grid_layout = self._create_grid(FIELDS["result"])

        frame_layout.addLayout(grid_layout)

        return frame

    def _create_plot_frame(self) -> SectionFrame:
        """Create the plot card with time/frequency tabs and diagrams."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        self._plot_tab = QTabWidget(frame)
        frame_layout.addWidget(self._plot_tab)

        widget_time_domain = self._create_time_domain_widget()
        self._plot_tab.addTab(widget_time_domain, TIME_DOMAIN)

        widget_frequency_domain = self._create_frequency_domain_widget()
        self._plot_tab.addTab(widget_frequency_domain, FREQUENCY_DOMAIN)

        widget_blockdiagram = self._create_block_diagram_widget()
        self._plot_tab.addTab(widget_blockdiagram, BLOCK_DIAGRAM)

        widget_tf = self._create_transfer_function_widget()
        self._plot_tab.addTab(widget_tf, TRANSFER_FUNCTION)

        return frame

    def _create_time_domain_widget(self) -> QWidget:
        """Create the time-domain plot widget."""
        container = QWidget(self)
        layout = self._create_card_layout()
        container.setLayout(layout)

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

        widget = PlotWidget(self._ui_context, self._vm_plots[TIME_DOMAIN], cl_plot_cfg, parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addWidget(widget)

        return container

    def _create_frequency_domain_widget(self) -> QWidget:
        """Create the frequency-domain Bode plot widget."""
        container = QWidget(self)
        layout = self._create_card_layout()
        container.setLayout(layout)

        widget = BodePlotWidget(self._ui_context, self._vm_plots[FREQUENCY_DOMAIN], parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(widget)

        return container

    def _create_block_diagram_widget(self) -> QWidget:
        """Create the closed-loop block diagram widget."""
        container = QWidget(self)
        layout = self._create_card_layout()
        container.setLayout(layout)

        svg_widget = AspectRatioSvgWidget()
        svg_widget.set_initial_scale(2)
        layout.addWidget(svg_widget)

        self.field_widgets.setdefault(BLOCK_DIAGRAM, svg_widget)
        self._load_block_diagram()

        return container

    def _create_transfer_function_widget(self) -> QWidget:
        """Create the transfer function summary widget."""
        container = QWidget(self)
        layout = self._create_card_layout()
        container.setLayout(layout)

        widget = QWidget(self)

        grid_layout = self._create_grid(FIELDS["tf"])
        widget.setLayout(grid_layout)

        tf = self._vm_evaluator.get_transfer_functions()

        tf: dict[EvaluationField, str] = {
            EvaluationField.TF_PLANT: tf.plant,
            EvaluationField.TF_CONTROLLER: tf.controller,
            EvaluationField.TF_OPEN_LOOP: tf.open_loop,
            EvaluationField.TF_CLOSED_LOOP: tf.closed_loop,
            EvaluationField.TF_SENSITIVITY: tf.sensitivity,
        }

        for key, value in tf.items():
            w: FormulaWidget
            w = self.field_widgets.get(key)

            w.set_formula(value)
            w.set_font_size(self._formula_font_size_scale)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(widget)

        return container

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        ...

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # vm evaluator
        self._vm_evaluator.closedLoopResponseChanged.connect(self._on_vm_closed_loop_compute_finished)
        self._vm_evaluator.plantResponseChanged.connect(self._on_vm_plant_compute_finished)
        self._vm_evaluator.functionChanged.connect(self._on_vm_compute_finished)
        self._vm_evaluator.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)
        self._vm_evaluator.plantFrequencyResponseChanged.connect(self._on_vm_frequency_computation_finished)
        self._vm_evaluator.closedLoopFrequencyResponseChanged.connect(self._on_vm_frequency_computation_finished)
        self._vm_evaluator.saveSvgRequested.connect(self._on_vm_save_svg_requested)

        # Plot ViewModel -> Function recomputation
        self._vm_plots[TIME_DOMAIN].xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plots[TIME_DOMAIN].xMaxChanged.connect(self._on_vm_time_changed)
        self._vm_plots[FREQUENCY_DOMAIN].xMinChanged.connect(self._on_vm_frequency_changed)
        self._vm_plots[FREQUENCY_DOMAIN].xMaxChanged.connect(self._on_vm_frequency_changed)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        super()._retranslate()

        self._lbl_title.setText(self.tr("Evaluation"))

        self._frm_result.setText(self.tr("PSO Result"))
        self._frm_plot.setText(self.tr("Closed Loop"))

        # translate pages
        self._plot_tab.setTabText(0, self.tr("Time Domain"))
        self._plot_tab.setTabText(1, self.tr("Frequency Domain"))
        self._plot_tab.setTabText(2, self.tr("Block Diagram"))
        self._plot_tab.setTabText(3, self.tr("Transfer Functions"))

        labels = {
            PsoResultField.RUN_TIME: self.tr("PSO run time"),
            PsoResultField.CONTROLLER_PARAMETERS: self.tr("Controller Parameters"),
            PsoResultField.FILTER_TIME_CONSTANT: self.tr("Filter Time Constant"),
            PsoResultField.PERFORMANCE_INDEX: self.tr("Performance Index"),
            PsoResultField.TIME_DOMAIN: self.tr("Time Domain"),
            PsoResultField.FREQUENCY_DOMAIN: self.tr("Frequency Domain"),

            EvaluationField.PLANT: self.tr("Plant"),
            EvaluationField.CONTROLLER: self.tr("Controller"),
            EvaluationField.OPEN_LOOP: self.tr("Open Loop"),
            EvaluationField.CLOSED_LOOP: self.tr("Closed Loop"),
            EvaluationField.SENSITIVITY: self.tr("Sensitivity"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        self._update_pso_result_values()

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        if not self._vm_evaluator.has_result():
            return

        self._sync_plot_time_window_from_model()

        self._update_time_domain_plots()
        self._update_frequency_domain_plots()
        self._update_pso_result_values()

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.evaluation, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))
        self._load_block_diagram()

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self.logger.debug(
            "Function finished computation -> updating plot (samples=%d)",
            len(t),
        )

        key = self._vm_evaluator.excitation_target.name

        self._vm_plots[TIME_DOMAIN].update_data(
            PlotData(
                key=PlotLabels[key].value,
                label=self._enum_translation(PlotLabels[key]),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels[key]),
                subplot_position=1,
            )
        )

    def _on_vm_closed_loop_compute_finished(self, t: ndarray, u: ndarray, y: ndarray) -> None:
        self.logger.debug(
            "Closed-loop response computation finished -> updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plots[TIME_DOMAIN].update_data(
            PlotData(
                key=PlotLabels.CLOSED_LOOP.value,
                label=self._enum_translation(PlotLabels.CLOSED_LOOP),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.CLOSED_LOOP),
                subplot_position=1,
            )
        )

        self._vm_plots[TIME_DOMAIN].update_data(
            PlotData(
                key=PlotLabels.CONTROL_SIGNAL.value,
                label=self._enum_translation(PlotLabels.CONTROL_SIGNAL),
                x=t,
                y=u,
                plot_style=PLOT_STYLE.get(PlotLabels.CONTROL_SIGNAL),
                subplot_position=2,
            )
        )

    def _on_vm_plant_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self.logger.debug(
            "Plant response computation finished -> updating response plot (samples=%d)",
            len(t),
        )
        self._vm_plots[TIME_DOMAIN].update_data(
            PlotData(
                key=PlotLabels.PLANT.value,
                label=self._enum_translation(PlotLabels.PLANT),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.PLANT),
                subplot_position=1,
            )
        )

    def _on_vm_frequency_computation_finished(self, result: FrequencyResponse) -> None:
        self.logger.debug(
            "Closed loop frequency response computation finished -> updating response plot (samples=%d)",
            len(result.omega)
        )

        keys = set(result.margin.keys()) | set(result.phase.keys())

        for key in keys:
            if key in PlotLabels.__members__:
                label_enum = PlotLabels[key]
            else:
                label_enum = PlotLabels(key)
            self._vm_plots[FREQUENCY_DOMAIN].update_data(
                BodePlotData(
                    key=label_enum.value,
                    label=self._enum_translation(label_enum),
                    omega=result.omega,
                    margin=result.margin[key],
                    phase=result.phase[key],
                    plot_style=PLOT_STYLE.get(label_enum),
                )
            )

    def _on_vm_pso_simulation_finished(self) -> None:
        self.logger.debug("PSO simulation finished -> refreshing excitation function")

        self._load_block_diagram()
        self._sync_plot_time_window_from_model()
        self._update_time_domain_plots()
        self._update_frequency_domain_plots()
        self._update_pso_result_values()

        widget: FormulaWidget = self.field_widgets[EvaluationField.TF_PLANT]
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return
        widget.set_formula(r"G(s) = " + snapshot.plant_tf)

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plots[TIME_DOMAIN].x_min
        t1 = self._vm_plots[TIME_DOMAIN].x_max

        self.logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._update_time_domain_plots()

    def _on_vm_frequency_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        omega_min = self._vm_plots[FREQUENCY_DOMAIN].x_min
        omega_max = self._vm_plots[FREQUENCY_DOMAIN].x_max

        self.logger.debug(f"Frequency range changed: {omega_min=}, {omega_max=}")
        self._update_frequency_domain_plots()

    # ============================================================
    # UI event handlers
    # ============================================================
    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        self._vm_plots[TIME_DOMAIN].x_min = self._vm_evaluator.t0
        self._vm_plots[TIME_DOMAIN].x_max = self._vm_evaluator.t1

    def _on_vm_save_svg_requested(self, request: dict[str, str]) -> None:
        self._save_svg_bundle(request)

    def _save_svg_bundle(self, request: dict[str, str]) -> None:
        block_diagram_target = Path(request[BLOCK_DIAGRAM])
        system_response_target = Path(request[TIME_DOMAIN])
        bode_plot_target = Path(request[FREQUENCY_DOMAIN])

        svg = self._build_block_diagram(False)

        self._vm_plots[TIME_DOMAIN].request_save_svg(str(system_response_target))
        self._vm_plots[FREQUENCY_DOMAIN].request_save_svg(str(bode_plot_target))
        save_svg(block_diagram_target, svg)
        self._vm_evaluator.notify_svg_export_finished()

    # ============================================================
    # Helpers
    # ============================================================
    def _update_time_domain_plots(self) -> None:
        t0 = self._vm_plots[TIME_DOMAIN].x_min
        t1 = self._vm_plots[TIME_DOMAIN].x_max

        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)
        self._vm_evaluator.compute_function(t0, t1)

    def _update_frequency_domain_plots(self) -> None:
        omega_min = self._vm_plots[FREQUENCY_DOMAIN].x_min
        omega_max = self._vm_plots[FREQUENCY_DOMAIN].x_max

        self._vm_evaluator.compute_plant_frequency_response(omega_min, omega_max)
        self._vm_evaluator.compute_closed_loop_frequency_response(omega_max, omega_min)

    def _update_pso_result_values(self) -> None:
        result = self._vm_evaluator.get_pso_result()
        snapshot = self._vm_evaluator.get_pso_snapshot()

        if result is None or snapshot is None:
            for key in PSO_RESULT_TEMPLATE.keys():
                self.field_widgets.get(key).setText("-")
            return

        limited_key = ""
        show_limited = False
        if result.tf_limited_sampling:
            limited_key = "sampling"
            show_limited = True
        elif result.tf_limited_simulation:
            limited_key = "simulation"
            show_limited = True

        text: dict[PsoResultField, PsoFieldText] = {
            PsoResultField.TIME: ({"time": result.simulation_time}, True),
            PsoResultField.ERROR_CRITERION: ({"error_criterion": self._enum_translation(snapshot.error_criterion),
                                              "value": result.error_criterion, }, True),
            PsoResultField.OVERSHOOT_CONTROL: ({"value": result.overshoot}, result.show_overshoot),
            PsoResultField.SLEW_RATE: ({"value": result.slew_rate}, True),
            PsoResultField.GAIN_MARGIN: ({"value": result.gain_margin, "omega": result.omega_180}, True),
            PsoResultField.PHASE_MARGIN: ({"value": result.phase_margin, "omega": result.omega_c}, True),
            PsoResultField.STABILITY_MARGIN: ({"value": result.stability_margin}, True),
            PsoResultField.KP: ({"kp": result.kp}, True),
            PsoResultField.TI: ({"ti": result.ti}, True),
            PsoResultField.TD: ({"td": result.td}, True),
            PsoResultField.TF: ({"tf": result.tf}, True),
            PsoResultField.TF_LIMITED: ({"limited": LIMITED_TEMPLATE.get(limited_key, "")}, show_limited),
            PsoResultField.MIN_SAMPLING_RATE: ({"sampling_rate": result.min_sampling_rate}, not show_limited),
        }

        for key, value in text.items():
            val_dict, visible = value
            widget = self.field_widgets.get(key)
            widget.setVisible(visible)
            widget.setText(self.tr(PSO_RESULT_TEMPLATE[key]) % val_dict)

    def _load_block_diagram(self) -> None:
        """Build and recolor the closed loop block diagram SVG."""
        svg = self._build_block_diagram()
        self.field_widgets.get(BLOCK_DIAGRAM).set_svg_bytes(svg.encode("utf-8"))

    def _build_block_diagram(self, use_color_mape: bool = True) -> str:
        """Build and recolor the closed loop block diagram SVG."""
        snapshot = self._vm_evaluator.get_pso_snapshot()
        if snapshot is None:
            return ""

        return load_closed_loop_diagram(
            snapshot.controller_anti_windup,
            (snapshot.controller_constraint_min, snapshot.controller_constraint_max),
            self._vm_theme.get_svg_color_map() if use_color_mape else None,
        )
