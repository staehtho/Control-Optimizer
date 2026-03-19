from typing import Any

from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QTabWidget, QHBoxLayout
from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from numpy import ndarray

from app_domain.controlsys import AntiWindup
from app_domain.ui_context import UiContext
from app_types import FrequencyResponse, EvaluationField, FieldConfig, PlotData, BodePlotData, PlotLabels, \
    SectionConfig, PsoResultField
from utils import SvgLayer, merge_svgs, recolor_svg
from viewmodels import EvaluationViewModel, PlotViewModel
from views import ViewMixin
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, SubplotConfiguration, SectionFrame, FormulaWidget, \
    BodePlotWidget, AspectRatioSvgWidget
from views.resources import BLOCK_DIAGRAM_DIR, BlockDiagram, Icons

TIME_DOMAIN = "time_domain"
FREQUENCY_DOMAIN = "frequency_domain"
TRANSFER_FUNCTION = "transfer_function"
BLOCK_DIAGRAM = "block_diagram"

FIELDS: dict[str, list[FieldConfig]] = {
    "tf": [
        FieldConfig(EvaluationField.PLANT, FormulaWidget),
        FieldConfig(EvaluationField.CONTROLLER, FormulaWidget),
        FieldConfig(EvaluationField.OPEN_LOOP, FormulaWidget),
        FieldConfig(EvaluationField.CLOSED_LOOP, FormulaWidget),
        FieldConfig(EvaluationField.SENSITIVITY, FormulaWidget),
        FieldConfig(EvaluationField.COMPLEMENTARY_SENSITIVITY, FormulaWidget),
    ],
    "result": [
        SectionConfig(PsoResultField.RUN_TIME, [
            FieldConfig(PsoResultField.TIME, QLabel, False)
        ]),
        SectionConfig(PsoResultField.PARAMETERS, [
            FieldConfig(PsoResultField.KP, QLabel, False),
            FieldConfig(PsoResultField.TI, QLabel, False),
            FieldConfig(PsoResultField.TD, QLabel, False),
            FieldConfig(PsoResultField.TF, QLabel, False),
        ])
    ]
}

PSO_RESULT_TEMPLATE: dict[PsoResultField, Any] = {
    PsoResultField.TIME: QT_TRANSLATE_NOOP("EvaluationView", "PSO finished after %(time).1f seconds."),
    PsoResultField.KP: QT_TRANSLATE_NOOP("EvaluationView", "Kp = %(kp).3f"),
    PsoResultField.TI: QT_TRANSLATE_NOOP("EvaluationView", "Ti = %(ti).3f"),
    PsoResultField.TD: QT_TRANSLATE_NOOP("EvaluationView", "Td = %(td).3f"),
    PsoResultField.TF: QT_TRANSLATE_NOOP("EvaluationView", "Tf = %(tf).3f"),
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
        icon = self._load_icon(Icons.evaluation, self._titel_icon_size)
        self._label_icon = QLabel(self)
        self._label_icon.setPixmap(icon.pixmap(self._titel_icon_size, self._titel_icon_size))
        self._label_icon.setFixedSize(self._titel_icon_size, self._titel_icon_size)

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
        self.setLayout(main_layout)

    def _create_result_frame(self) -> SectionFrame:
        """Create the PSO result summary card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        grid_layout = self._create_grid(FIELDS.get("result"))

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

        widget = PlotWidget(self._ui_context, self._vm_plots.get(TIME_DOMAIN), cl_plot_cfg, parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        return widget

    def _create_frequency_domain_widget(self) -> QWidget:
        """Create the frequency-domain Bode plot widget."""
        widget = BodePlotWidget(self._ui_context, self._vm_plots.get(FREQUENCY_DOMAIN), parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        return widget

    def _create_block_diagram_widget(self) -> QWidget:
        """Create the closed-loop block diagram widget."""

        svg_widget = AspectRatioSvgWidget()
        svg_widget.set_initial_scale(2)
        self.field_widgets.setdefault(BLOCK_DIAGRAM, svg_widget)
        self._load_block_diagram()

        return svg_widget

    def _create_transfer_function_widget(self) -> QWidget:
        """Create the transfer function summary widget."""
        widget = QWidget(self)

        grid_layout = self._create_grid(FIELDS.get("tf"))
        widget.setLayout(grid_layout)

        tf: dict[EvaluationField, str] = {
            EvaluationField.PLANT: self._vm_evaluator.plant_tf,
            EvaluationField.CONTROLLER: r"C(S) = ",
            EvaluationField.OPEN_LOOP: r"L(S) = C(S) \cdot G(S)",
            EvaluationField.CLOSED_LOOP: r"",
            EvaluationField.SENSITIVITY: r"",
            EvaluationField.COMPLEMENTARY_SENSITIVITY: r"",
        }

        for key, value in tf.items():
            w: FormulaWidget
            w = self.field_widgets.get(key)

            w.set_formula(value)
            w.set_font_size(self._formula_font_size_scale)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft)

        return widget

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

        # Plot ViewModel -> Function recomputation
        self._vm_plots.get(TIME_DOMAIN).xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plots.get(TIME_DOMAIN).xMaxChanged.connect(self._on_vm_time_changed)
        self._vm_plots.get(FREQUENCY_DOMAIN).xMinChanged.connect(self._on_vm_frequency_changed)
        self._vm_plots.get(FREQUENCY_DOMAIN).xMaxChanged.connect(self._on_vm_frequency_changed)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Evaluation"))
        self._frm_result.set_title(self.tr("PSO Result"))
        self._frm_plot.set_title(self.tr("Closed Loop"))

        # translate pages
        self._plot_tab.setTabText(0, self.tr("Time Domain"))
        self._plot_tab.setTabText(1, self.tr("Frequency Domain"))
        self._plot_tab.setTabText(2, self.tr("Block Diagram"))

        labels = {
            PsoResultField.RUN_TIME: self.tr("PSO run time"),
            PsoResultField.PARAMETERS: self.tr("Controller Parameters"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        self._update_pso_result_values()

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._sync_plot_time_window_from_model()

        self._update_time_domain_plots()
        self._update_frequency_domain_plots()
        self._update_pso_result_values()

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.evaluation, self._titel_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._titel_icon_size, self._titel_icon_size))
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

        self._vm_plots.get(TIME_DOMAIN).update_data(
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
        self._vm_plots.get(TIME_DOMAIN).update_data(
            PlotData(
                key=PlotLabels.CLOSED_LOOP.value,
                label=self._enum_translation(PlotLabels.CLOSED_LOOP),
                x=t,
                y=y,
                plot_style=PLOT_STYLE.get(PlotLabels.CLOSED_LOOP),
                subplot_position=1,
            )
        )

        self._vm_plots.get(TIME_DOMAIN).update_data(
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
        self._vm_plots.get(TIME_DOMAIN).update_data(
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
            self._vm_plots.get(FREQUENCY_DOMAIN).update_data(
                BodePlotData(
                    key=label_enum.value,
                    label=self._enum_translation(label_enum),
                    omega=result.omega,
                    margin=result.margin.get(key),
                    phase=result.phase.get(key),
                    plot_style=PLOT_STYLE.get(label_enum),
                )
            )

    def _on_vm_pso_simulation_finished(self) -> None:
        self.logger.debug("PSO simulation finished -> refreshing excitation function")

        self._update_pso_result_values()
        self._apply_init_value()

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plots.get(TIME_DOMAIN).x_min
        t1 = self._vm_plots.get(TIME_DOMAIN).x_max

        self.logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._update_time_domain_plots()

    def _on_vm_frequency_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        omega_min = self._vm_plots.get(FREQUENCY_DOMAIN).x_min
        omega_max = self._vm_plots.get(FREQUENCY_DOMAIN).x_max

        self.logger.debug(f"Frequency range changed: {omega_min=}, {omega_max=}")
        self._update_frequency_domain_plots()

    # ============================================================
    # UI event handlers
    # ============================================================
    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        self._vm_plots.get(TIME_DOMAIN).x_min = self._vm_evaluator.t0
        self._vm_plots.get(TIME_DOMAIN).x_max = self._vm_evaluator.t1

    # ============================================================
    # Helpers
    # ============================================================
    def _update_time_domain_plots(self) -> None:
        t0 = self._vm_plots.get(TIME_DOMAIN).x_min
        t1 = self._vm_plots.get(TIME_DOMAIN).x_max

        self._vm_evaluator.compute_closed_loop_response(t0, t1)
        self._vm_evaluator.compute_plant_response(t0, t1)
        self._vm_evaluator.compute_function(t0, t1)

    def _update_frequency_domain_plots(self) -> None:
        omega_min = self._vm_plots.get(FREQUENCY_DOMAIN).x_min
        omega_max = self._vm_plots.get(FREQUENCY_DOMAIN).x_max

        self._vm_evaluator.compute_plant_frequency_response(omega_min, omega_max)
        self._vm_evaluator.compute_closed_loop_frequency_response(omega_max, omega_min)

    def _update_pso_result_values(self) -> None:
        result = self._vm_evaluator.get_pso_result()
        if result is None:
            for key in PSO_RESULT_TEMPLATE.keys():
                self.field_widgets.get(key).setText("-")
            return

        pso_result = self._vm_evaluator.get_pso_result()

        text = {
            PsoResultField.TIME: {"time": pso_result.simulation_time},
            PsoResultField.KP: {"kp": pso_result.kp},
            PsoResultField.TI: {"ti": pso_result.ti},
            PsoResultField.TD: {"td": pso_result.td},
            PsoResultField.TF: {"tf": pso_result.tf}
        }

        for key, value in text.items():
            self.field_widgets.get(key).setText(PSO_RESULT_TEMPLATE.get(key) % value)

    def _load_block_diagram(self) -> None:
        """Build and recolor the closed loop block diagram SVG."""
        x_offset = 100
        y = 125
        node_x = 150
        sum_x = 475
        svgs = [
            (BlockDiagram.closed_loop, (0, 0)),
            (BlockDiagram.controller_in, (x_offset, y)),
            (BlockDiagram.controller_out, (sum_x + x_offset, y)),
            (BlockDiagram.p_path, (node_x + x_offset, y)),
            (BlockDiagram.d_path, (node_x + x_offset, y))
        ]

        match self._vm_evaluator.anti_windup:
            case AntiWindup.BACKCALCULATION:
                svgs.append((BlockDiagram.backcalculation, (node_x + x_offset, y)))
            case AntiWindup.CLAMPING:
                svgs.append((BlockDiagram.clamping, (node_x + x_offset, y)))
            case AntiWindup.CONDITIONAL:
                svgs.append((BlockDiagram.conditional, (node_x + x_offset, y)))
            case unknown_value:
                raise ValueError(
                    f"Unsupported anti-windup method: {unknown_value!r}. "
                    "Expected one of: BACKCALCULATION, CLAMPING, CONDITIONAL."
                )

        svg_layers = []
        for svg, translate in svgs:
            svg_path = BLOCK_DIAGRAM_DIR / svg
            svg_layers.append(SvgLayer(svg_path.read_text(encoding="utf-8"), translate=translate))

        merged_svg = merge_svgs(svg_layers)

        # set min and max constraint
        merged_svg = merged_svg.replace("min: ###", f"min: {self._vm_evaluator.constraint_min}")
        merged_svg = merged_svg.replace("max: ###", f"max: {self._vm_evaluator.constraint_max}")

        recolored = recolor_svg(merged_svg, self._vm_theme.get_svg_color_map())
        self.field_widgets.get(BLOCK_DIAGRAM).set_svg_bytes(recolored.encode("utf-8"))
