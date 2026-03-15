from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QTabWidget, QHBoxLayout, QGridLayout
from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from numpy import ndarray

from app_domain.controlsys import AntiWindup
from app_domain.ui_context import UiContext
from app_types import FrequencyResponse, EvaluationField, FieldConfig, PlotData, BodePlotData, PlotLabels
from utils import SvgLayer, merge_svgs, recolor_svg
from viewmodels import EvaluationViewModel, PlotViewModel
from views import BaseView
from views.plot_style import PLOT_STYLE
from views.widgets import PlotWidget, PlotWidgetConfiguration, SubplotConfiguration, SectionFrame, FormulaWidget, \
    BodePlotWidget, AspectRatioSvgWidget
from views.resources import BLOCK_DIAGRAM_DIR, BlockDiagram, Icons

TIME_DOMAIN = "time_domain"
FREQUENCY_DOMAIN = "frequency_domain"
TRANSFER_FUNCTION = "transfer_function"
BLOCK_DIAGRAM = "block_diagram"

PSO_RESULT_FIELDS = [
    ("simulation_time", QT_TRANSLATE_NOOP("EvaluationViewMixin", "Simulation Time [s]")),
    ("kp", QT_TRANSLATE_NOOP("EvaluationViewMixin", "Kp")),
    ("ti", QT_TRANSLATE_NOOP("EvaluationViewMixin", "Ti")),
    ("td", QT_TRANSLATE_NOOP("EvaluationViewMixin", "Td")),
    ("tf", QT_TRANSLATE_NOOP("EvaluationViewMixin", "Tf")),
]

FIELDS: list[FieldConfig] = [
    FieldConfig(EvaluationField.PLANT, FormulaWidget),
    FieldConfig(EvaluationField.CONTROLLER, FormulaWidget),
    FieldConfig(EvaluationField.OPEN_LOOP, FormulaWidget),
    FieldConfig(EvaluationField.CLOSED_LOOP, FormulaWidget),
    FieldConfig(EvaluationField.SENSITIVITY, FormulaWidget),
    FieldConfig(EvaluationField.COMPLEMENTARY_SENSITIVITY, FormulaWidget),
]


class EvaluationViewMixin(ViewMixin, QWidget):
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
        self._pso_caption_labels: dict[str, QLabel] = {}
        self._pso_value_labels: dict[str, QLabel] = {}

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
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
        frame: SectionFrame
        frame, frame_layout = self._create_card(self)

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(12)
        grid_layout.setVerticalSpacing(6)

        for row, (key, _label) in enumerate(PSO_RESULT_FIELDS):
            caption = QLabel(frame)
            value = QLabel(frame)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self._pso_caption_labels[key] = caption
            self._pso_value_labels[key] = value

            grid_layout.addWidget(caption, row, 0)
            grid_layout.addWidget(value, row, 1)

        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        frame_layout.addLayout(grid_layout)

        return frame

    def _create_plot_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, frame_layout = self._create_card(self)

        self._plot_tab = QTabWidget(frame)
        frame_layout.addWidget(self._plot_tab)

        widget_time_domain = self._create_time_domain_widget()
        self._plot_tab_pages.setdefault(TIME_DOMAIN, widget_time_domain)
        self._plot_tab.addTab(widget_time_domain, TIME_DOMAIN)

        widget_frequency_domain = self._create_frequency_domain_widget()
        self._plot_tab_pages.setdefault(FREQUENCY_DOMAIN, widget_frequency_domain)
        self._plot_tab.addTab(widget_frequency_domain, FREQUENCY_DOMAIN)

        widget_blockdiagram = self._create_block_diagram_widget()
        self._plot_tab_pages.setdefault(BLOCK_DIAGRAM, widget_blockdiagram)
        self._plot_tab.addTab(widget_blockdiagram, BLOCK_DIAGRAM)

        widget_tf = self._create_transfer_function_widget()
        self._plot_tab_pages.setdefault(TRANSFER_FUNCTION, widget_tf)
        self._plot_tab.addTab(widget_tf, TRANSFER_FUNCTION)

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

        widget = PlotWidget(self._ui_context, self._vm_plots.get(TIME_DOMAIN), cl_plot_cfg, parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        return widget

    def _create_frequency_domain_widget(self) -> QWidget:
        widget = BodePlotWidget(self._ui_context, self._vm_plots.get(FREQUENCY_DOMAIN), parent=self._plot_tab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        return widget

    def _create_block_diagram_widget(self) -> QWidget:
        svgs = [
            (BlockDiagram.closed_loop, (0, 0)),
            (BlockDiagram.controller_base, (100, 0)),
            (BlockDiagram.p_path, (100, 0)),
            (BlockDiagram.d_path, (100, 0))
        ]

        match self._vm_evaluator.anti_windup:
            case AntiWindup.BACKCALCULATION:
                svgs.append((BlockDiagram.backcalculation, (100, 0)))
            case AntiWindup.CLAMPING:
                svgs.append((BlockDiagram.clamping, (100, 0)))
            case AntiWindup.CONDITIONAL:
                svgs.append((BlockDiagram.conditional, (100, 0)))
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
        recolored = recolor_svg(merged_svg, self._vm_theme.get_svg_color_map())
        return AspectRatioSvgWidget(svg_bytes=recolored.encode("utf-8"), initial_scale=2)

    def _create_transfer_function_widget(self) -> QWidget:

        widget = QWidget(self)

        grid_layout = self._create_grid(FIELDS, 4)
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
            w = self._field_widgets.get(key)

            w.set_formula(value)
            w.set_font_size(self._formula_font_size_scale)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft)

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
        self._vm_plots.get(TIME_DOMAIN).xMinChanged.connect(self._on_vm_time_changed)
        self._vm_plots.get(TIME_DOMAIN).xMaxChanged.connect(self._on_vm_time_changed)
        self._vm_plots.get(FREQUENCY_DOMAIN).xMinChanged.connect(self._on_vm_frequency_changed)
        self._vm_plots.get(FREQUENCY_DOMAIN).xMaxChanged.connect(self._on_vm_frequency_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Evaluation"))
        self._frm_result.set_title(self.tr("PSO Result"))
        self._frm_plot.set_title(self.tr("Closed Loop"))

        # translate pages
        self._plot_tab.setTabText(0, self.tr("Time Domain"))
        self._plot_tab.setTabText(1, self.tr("Frequency Domain"))
        self._plot_tab.setTabText(2, self.tr("Block Diagram"))

        for key, label in PSO_RESULT_FIELDS:
            caption = self._pso_caption_labels.get(key)
            if caption is not None:
                caption.setText(self.tr(label))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._sync_plot_time_window_from_model()

        self._update_time_domain_plots()
        self._update_frequency_domain_plots()
        self._update_pso_result_values()

    # -------------------------------------------------
    # Applied theme
    # -------------------------------------------------
    def _on_theme_applied(self) -> None:
        icon = self._load_icon(Icons.evaluation, self._titel_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._titel_icon_size, self._titel_icon_size))

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_compute_finished(self, t: ndarray, y: ndarray) -> None:
        self._logger.debug(
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
        self._logger.debug(
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
        self._logger.debug(
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
        self._logger.debug(
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
        self._logger.debug("PSO simulation finished -> refreshing excitation function")

        self._update_pso_result_values()
        self._apply_init_value()

    def _on_vm_time_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        t0 = self._vm_plots.get(TIME_DOMAIN).x_min
        t1 = self._vm_plots.get(TIME_DOMAIN).x_max

        self._logger.debug(f"Time range changed: t0={t0}, t1={t1}")
        self._update_time_domain_plots()

    def _on_vm_frequency_changed(self) -> None:
        """Trigger recomputation when plot time range changes."""
        omega_min = self._vm_plots.get(FREQUENCY_DOMAIN).x_min
        omega_max = self._vm_plots.get(FREQUENCY_DOMAIN).x_max

        self._logger.debug(f"Frequency range changed: {omega_min=}, {omega_max=}")
        self._update_frequency_domain_plots()

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _sync_plot_time_window_from_model(self) -> None:
        """Sync plot time range from persisted evaluator state via evaluator VM."""
        self._vm_plots.get(TIME_DOMAIN).x_min = self._vm_evaluator.t0
        self._vm_plots.get(TIME_DOMAIN).x_max = self._vm_evaluator.t1

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
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
            for label in self._pso_value_labels.values():
                label.setText("-")
            return

        values = {
            "simulation_time": result.simulation_time,
            "kp": result.kp,
            "ti": result.ti,
            "td": result.td,
            "tf": result.tf,
        }

        for key, value in values.items():
            label = self._pso_value_labels.get(key)
            if label is not None:
                label.setText(self._format_value(value))
