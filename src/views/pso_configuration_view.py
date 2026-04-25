from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar, QHBoxLayout, QSizePolicy, QLayout,
    QGraphicsOpacityEffect, QVBoxLayout
)
from PySide6.QtGui import QDoubleValidator, QIntValidator, Qt

from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from app_domain.functions import FunctionTypes
from app_types import PsoField, FieldConfig, SectionConfig, ConnectSignalConfig, get_performance_tooltip, NavLabels
from views.view_mixin import ViewMixin
from views.widgets import FormulaWidget, AspectRatioSvgWidget, ToggleSwitch, ToggleableSectionFrame
from resources.resources import Icons
from resources.blockdiagram import load_closed_loop_diagram

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from viewmodels import PlantViewModel, FunctionViewModel, PsoConfigurationViewModel, ControllerViewModel
    from views.widgets import SectionFrame

FIELDS_LEFT: list[FieldConfig | SectionConfig] = [
    SectionConfig(PsoField.PLANT, [
        FieldConfig(PsoField.PLANT_TF, FormulaWidget, False),
        FieldConfig("", QLabel, False),
    ]),
    SectionConfig(PsoField.SIMULATION_TIME, [
        FieldConfig(PsoField.T0, QLineEdit),
        FieldConfig(PsoField.T1, QLineEdit),
    ]),
    SectionConfig(PsoField.PERFORMANCE_INDEX, [
        SectionConfig(PsoField.TIME_DOMAIN, [
            FieldConfig(PsoField.ERROR_CRITERION, QComboBox),
            FieldConfig(
                PsoField.OVERSHOOT_CONTROL, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6), toggleable=True
            ),
            SectionConfig(PsoField.SLEW_RATE_LIMITER, [
                FieldConfig(PsoField.SLEW_RATE_MAX, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6)),
                # TODO: max value?
                FieldConfig(PsoField.SLEW_WINDOW_SIZE, QLineEdit, validator=QIntValidator(0, 1000000)),
            ], toggleable=True)
        ]),
        SectionConfig(PsoField.FREQUENCY_DOMAIN, [
            FieldConfig(PsoField.GAIN_MARGIN, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6), toggleable=True),
            FieldConfig(PsoField.PHASE_MARGIN, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6), toggleable=True),
            FieldConfig(PsoField.STABILITY_MARGIN, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6), toggleable=True)
        ])
    ]),
]

FIELDS_RIGHT: list[FieldConfig | SectionConfig] = [
    SectionConfig(PsoField.EXCITATION, [
        FieldConfig(PsoField.FUNCTION_FORMULA, FormulaWidget, False),
        FieldConfig(PsoField.EXCITATION_TARGET, QComboBox),
    ]),
    SectionConfig(PsoField.PSO_BOUNDS, [
    ]),
]

class PsoConfigurationView(ViewMixin, QWidget):
    """View for configuring PSO parameters and running simulations."""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(
            self,
            ui_context: UiContext,
            vm_plant: PlantViewModel,
            vm_function: FunctionViewModel,
            vm_controller: ControllerViewModel,
            vm_pso: PsoConfigurationViewModel,
            parent: QWidget = None,
    ):
        QWidget.__init__(self, parent)

        self._vm_plant = vm_plant
        self._vm_function = vm_function
        self._vm_controller = vm_controller
        self._vm_pso = vm_pso

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.pso_parameter, self._title_icon_size)
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

        self._frm_block_diagram = self._create_block_diagram_frame()
        main_layout.addWidget(self._frm_block_diagram)

        self._frm_run_pso = self._create_run_pso_frame()
        main_layout.addWidget(self._frm_run_pso)

        main_layout.addLayout(self._create_field_grid())
        self._on_vm_controller_type_changed()

        main_layout.addLayout(self._create_navigation_buttons_layout())

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_block_diagram_frame(self) -> SectionFrame:
        """Create the block diagram control card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        svg_widget = AspectRatioSvgWidget()
        svg_widget.set_initial_scale(4)
        svg_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        svg_widget.setMinimumHeight(400)
        frame_layout.addWidget(svg_widget)
        self.field_widgets[PsoField.BLOCK_DIAGRAM] = svg_widget

        return frame

    def _create_field_grid(self) -> QLayout:
        """Create the field grid layout."""
        layout = QHBoxLayout()

        # Left column
        left_col = QVBoxLayout()
        left_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Right column
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addLayout(left_col)
        layout.addLayout(right_col)

        left_col.addLayout(self._create_grid(FIELDS_LEFT, columns=2))
        right_col.addLayout(self._create_grid(FIELDS_RIGHT, columns=2))

        self.field_widgets[PsoField.PLANT_TF].set_font_size(self._formula_font_size_scale)
        self.field_widgets[PsoField.FUNCTION_FORMULA].set_font_size(self._formula_font_size_scale)

        self._frm_pso_bounds: SectionFrame = self.labels[PsoField.PSO_BOUNDS]

        return layout

    def _create_run_pso_frame(self) -> SectionFrame:
        """Create the PSO run control card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        self._progress_bar = QProgressBar(frame)
        self._progress_bar.setMinimum(0)
        self._progress_bar.setValue(0)
        frame_layout.addWidget(self._progress_bar)


        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self._lbl_interrupt_status = QLabel(frame)
        self._lbl_interrupt_status.setObjectName("statusText")
        self._lbl_interrupt_status.setText("")
        btn_layout.addWidget(self._lbl_interrupt_status)

        btn_layout.addStretch()

        self._btn_run_pso = QPushButton(frame)
        self._btn_run_pso.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_layout.addWidget(self._btn_run_pso)
        self.labels[PsoField.RUN_PSO] = self._btn_run_pso

        self._btn_interrupt_pso = QPushButton(frame)
        self._btn_interrupt_pso.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_interrupt_pso.setEnabled(False)
        btn_layout.addWidget(self._btn_interrupt_pso)
        self.labels[PsoField.INTERRUPT_PSO] = self._btn_interrupt_pso

        frame_layout.addLayout(btn_layout)

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""

        self._connect_object_signals(self._get_widget_bindings())
        self._connect_object_signals(self._get_pso_bounds_widget_bindings())

        self._btn_run_pso.clicked.connect(self._on_btn_run_pso)
        self._btn_interrupt_pso.clicked.connect(self._on_btn_interrupt_pso)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # Plant ViewModel
        self._vm_plant.polyTfChanged.connect(self._on_vm_plant_tf_changed)
        self._vm_plant.isValidChanged.connect(self._on_vm_plant_is_valid_changed)

        # Function ViewModel
        self._vm_function.functionChanged.connect(self._on_vm_function_function_changed)

        # Controller ViewModel
        self._vm_controller.controllerTypeChanged.connect(self._on_vm_controller_type_changed)
        self._vm_controller.antiWindupChanged.connect(self._load_closed_loop_block_diagram)
        self._vm_controller.constraintMinChanged.connect(self._load_closed_loop_block_diagram)
        self._vm_controller.constraintMaxChanged.connect(self._load_closed_loop_block_diagram)

        # PSO Configuration ViewModel
        self._vm_pso.validationFailed.connect(self._on_validation_failed)
        self._vm_pso.overshootControlVisibilityChanged.connect(self._on_vm_overshoot_control_visibility_changed)

        configs = self._get_vm_bindings()
        configs.extend(self._get_pso_bounds_vm_bindings())
        configs.extend(self._get_toggle_vm_bindings())
        self._connect_object_signals(configs)

        self._vm_pso.psoProgressChanged.connect(self._on_vm_pso_progress_changed)
        self._vm_pso.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)
        self._vm_pso.psoSimulationInterrupted.connect(self._on_vm_pso_simulation_interrupted)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        super()._retranslate()

        self._lbl_title.setText(self._enum_translation(NavLabels.PSO_PARAMETER))
        self._frm_block_diagram.setText(self.tr("Closed Loop Block Diagram"))
        self._frm_run_pso.setText(self.tr("PSO Simulation"))

        labels = {
            PsoField.PLANT: self.tr("Plant"),
            PsoField.EXCITATION: self.tr("Excitation Function"),
            PsoField.EXCITATION_TARGET: self.tr("Excitation Target"),
            PsoField.SIMULATION_TIME: self.tr("Simulation Time"),
            PsoField.T0: self.tr("Start Time [s]"),
            PsoField.T1: self.tr("End Time [s]"),
            PsoField.PERFORMANCE_INDEX: self.tr("Performance Index"),
            PsoField.TIME_DOMAIN: self.tr("Time Domain"),
            PsoField.ERROR_CRITERION: self.tr("Error Criterion"),
            PsoField.OVERSHOOT_CONTROL: self.tr("Max Overshoot [%]"),
            PsoField.SLEW_RATE_LIMITER: self.tr("Slew Rate Limit"),
            PsoField.SLEW_RATE_MAX: self.tr("Maximum du/dt"),
            PsoField.SLEW_WINDOW_SIZE: self.tr("Window Size"),
            PsoField.FREQUENCY_DOMAIN: self.tr("Frequency Domain"),
            PsoField.GAIN_MARGIN: self.tr("Gain margin [dB]"),
            PsoField.PHASE_MARGIN: self.tr("Phase margin [°]"),
            PsoField.STABILITY_MARGIN: self.tr("Stability margin [dB]"),
            PsoField.PSO_BOUNDS: self.tr("PSO Bounds"),
            PsoField.RUN_PSO: self.tr("Start PSO Simulation"),
            PsoField.INTERRUPT_PSO: self.tr("Interrupt"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        enums = {PsoField.EXCITATION_TARGET: ExcitationTarget, PsoField.ERROR_CRITERION: PerformanceIndex}
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self.field_widgets[key], data)

        self._retranslate_pso_bounds()
        self._apply_tool_tips()

    def _retranslate_pso_bounds(self) -> None:
        """Update all PSO bounds text after a language change."""

        for key in self.labels:
            if PsoField.PSO_BOUNDS_KEY.value not in key:
                continue

            if PsoField.PSO_LOWER_KEY.value in key:
                self.labels[key].setText(self.tr("Minimum"))
                continue

            if PsoField.PSO_UPPER_KEY.value in key:
                self.labels[key].setText(self.tr("Maximum"))
                continue

            self.labels[key].setText(self.tr("%(param_name)s bounds") % {"param_name": str(key.split('.')[0]).title()})


    def _apply_tool_tips(self) -> None:

        tool_tips: dict[PsoField, Any] = {
            PsoField.OVERSHOOT_CONTROL: self.tr(
                """Specifies the maximum allowed overshoot as a percentage.
                This setting is only available for excitation type %(excitation_target)s and function type %(function_type)s."""
            ) % {
                "excitation_target": self._enum_translation(ExcitationTarget.REFERENCE),
                "function_type": self._enum_translation(FunctionTypes.STEP),
            },
            PsoField.SLEW_RATE_MAX: self.tr(
                """Limits the maximum rate of change of the controller output du/dt.
                This constrains how quickly the control signal u can change over time,
                helping to prevent actuator saturation and excessive dynamics."""
            ),
            PsoField.SLEW_WINDOW_SIZE: self.tr(
                """Defines the time window used to compute the rate of change du/dt of the controller output.
                Larger windows provide smoother estimates, while smaller windows increase sensitivity to rapid changes."""
            ),
            PsoField.GAIN_MARGIN: self.tr(
                """Defines the minimum required gain margin (in dB).
                Ensures sufficient robustness by specifying how much the open loop gain can increase before instability occurs."""
            ),
            PsoField.PHASE_MARGIN: self.tr(
                """Defines the minimum required phase margin (in degrees).
                Ensures adequate stability by limiting the allowable additional phase lag before instability."""
            ),
            PsoField.STABILITY_MARGIN: self.tr(
                """Defines the maximum allowed sensitivity (in dB).
                Limits how strongly the closed loop system responds to disturbances and model uncertainties."""
            )
        }

        for key, tool_tip in tool_tips.items():
            field = self.field_widgets[key]
            field.setToolTip(tool_tip)

        self._apply_tool_tip_error_criterion()

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            PsoField.T0: self._vm_pso.t0,
            PsoField.T1: self._vm_pso.t1,
            PsoField.OVERSHOOT_CONTROL: self._vm_pso.overshoot_control,
            PsoField.SLEW_RATE_MAX: self._vm_pso.slew_rate_max,
            PsoField.SLEW_WINDOW_SIZE: self._vm_pso.slew_window_size,
            PsoField.GAIN_MARGIN: self._vm_pso.gain_margin,
            PsoField.PHASE_MARGIN: self._vm_pso.phase_margin,
            PsoField.STABILITY_MARGIN: self._vm_pso.stability_margin,
        }
        for key, value in init_value.items():
            self.field_widgets[key].setText(f"{value}")

        attributes: dict[PsoField, str] = {
            PsoField.EXCITATION_TARGET: "excitation_target",
            PsoField.ERROR_CRITERION: "error_criterion",
        }
        for key, attr in attributes.items():
            index = self.field_widgets[key].findData(getattr(self._vm_pso, attr))
            if index >= 0:
                self.field_widgets[key].setCurrentIndex(index)

        self._btn_run_pso.setEnabled(self._vm_plant.is_valid)
        self._btn_interrupt_pso.setEnabled(False)

        self._set_formula_tf()
        self._set_formula_function()

        self._set_formula_tf()
        self._set_formula_function()
        self._apply_init_value_pos_bounds()

        self._btn_nav_next.setEnabled(False)
        effect = self._btn_nav_next.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self._btn_nav_next)
            self._btn_nav_next.setGraphicsEffect(effect)

        effect.setOpacity(self._opacity_disabled)

        self._sync_toggle_states()
        self._vm_pso.check_overshoot_control_visibility()
        self._load_closed_loop_block_diagram()

    def _apply_init_value_pos_bounds(self) -> None:
        """Apply initial values to the PSO bounds."""

        lw = self._vm_pso.get_lower_bounds()
        up = self._vm_pso.get_upper_bounds()

        for key in self.field_widgets.keys():
            if PsoField.PSO_BOUNDS_KEY.value not in key:
                continue

            k = str(key.split('.')[0])

            if PsoField.PSO_LOWER_KEY.value in key:
                self.field_widgets[key].setText(f"{lw[k]}")
                continue

            if PsoField.PSO_UPPER_KEY.value in key:
                self.field_widgets[key].setText(f"{up[k]}")
                continue

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.pso_parameter, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))

        self._set_formula_tf()
        self._set_formula_function()
        self._load_closed_loop_block_diagram()

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_vm_plant_tf_changed(self) -> None:
        """Update the plant transfer function formula when it changes."""
        self._set_formula_tf()

    def _on_vm_function_function_changed(self) -> None:
        """Update the excitation function formula when it changes."""
        self._set_formula_function()

        self._vm_pso.check_overshoot_control_visibility()

    def _load_closed_loop_block_diagram(self) -> None:
        """Build and recolor the closed loop block diagram SVG."""
        merged_svg = load_closed_loop_diagram(
            self._vm_controller.anti_windup,
            (self._vm_controller.constraint_min, self._vm_controller.constraint_max),
            self._vm_theme.get_svg_color_map(),
        )
        self.field_widgets[PsoField.BLOCK_DIAGRAM].set_svg_bytes(merged_svg.encode("utf-8"))

    def _on_vm_pso_simulation_finished(self) -> None:
        """Re-enable the run button after PSO simulation completes."""
        self._btn_run_pso.setEnabled(True)
        self._btn_interrupt_pso.setEnabled(False)

        self._btn_nav_next.setEnabled(True)
        effect = self._btn_nav_next.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self._btn_nav_next)
            self._btn_nav_next.setGraphicsEffect(effect)

        effect.setOpacity(1.0)

    def _on_vm_pso_simulation_interrupted(self) -> None:
        """Re-enable the run button after PSO simulation interruption."""
        self._btn_run_pso.setEnabled(self._vm_plant.is_valid)
        self._btn_interrupt_pso.setEnabled(False)
        self._lbl_interrupt_status.setText(self.tr("Interrupted"))

    def _on_vm_field_enabled_changed(self, **kwargs: Any) -> None:
        is_enabled = kwargs.get("is_enabled")
        if not isinstance(is_enabled, Callable) or is_enabled is None:
            raise TypeError(f"Expected Callable, got {type(is_enabled)}")
        enabled = is_enabled()

        lable = kwargs.get("lable")
        if not isinstance(lable, (ToggleSwitch, ToggleableSectionFrame)) or lable is None:
            raise TypeError(f"Expected QLabel, got {type(lable)}")

        if lable.isChecked() != enabled:
            lable.set_checked_no_anim(enabled)

        if isinstance(lable, ToggleableSectionFrame):
            for child in lable.content_widget.findChildren(QWidget):
                effect = child.graphicsEffect()
                if not isinstance(effect, QGraphicsOpacityEffect):
                    effect = QGraphicsOpacityEffect(child)
                    child.setGraphicsEffect(effect)
                effect.setOpacity(1.0 if enabled else self._opacity_disabled)

        field = kwargs.get("field")
        if field is None:
            return

        if not isinstance(field, QLineEdit):
            raise TypeError(f"Expected QLineEdit, got {type(field)}")

        field.setEnabled(enabled)
        effect = field.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(field)
            field.setGraphicsEffect(effect)

        effect.setOpacity(1.0 if enabled else self._opacity_disabled)

    def _on_vm_overshoot_control_visibility_changed(self) -> None:
        # set opacity to hide the overshoot control
        lbl = self.labels.get(PsoField.OVERSHOOT_CONTROL)
        widget = self.field_widgets.get(PsoField.OVERSHOOT_CONTROL)
        visible = self._vm_pso.overshoot_control_visibility
        enabled = self._vm_pso.overshoot_control_enabled

        lbl.setEnabled(visible)
        eff = lbl.graphicsEffect()
        if eff is None:
            eff = QGraphicsOpacityEffect(lbl)
            lbl.setGraphicsEffect(eff)
        eff.setOpacity(1.0 if visible else 0.0)

        widget.setEnabled(visible and enabled)
        eff = widget.graphicsEffect()
        if eff is None:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)

        if visible and enabled:
            eff.setOpacity(1.0)
        if visible and not enabled:
            eff.setOpacity(self._opacity_disabled)
        if not visible:
            eff.setOpacity(0.0)

    def _on_vm_controller_type_changed(self) -> None:
        self._rebuild_pso_bounds_fields()
        self._connect_object_signals(self._get_pso_bounds_widget_bindings())
        self._retranslate_pso_bounds()
        self._apply_init_value_pos_bounds()

    def _on_vm_pso_bounds_changed(self, key: str, bound_key: str) -> None:
        field_key = f"{key}.{bound_key}.{PsoField.PSO_BOUNDS_KEY.value}"
        field = self.field_widgets.get(field_key)
        if field is None:
            return

        if bound_key == PsoField.PSO_LOWER_KEY.value:
            bounds = self._vm_pso.get_lower_bounds()
        else:
            bounds = self._vm_pso.get_upper_bounds()

        self._on_vm_changed(
            self,
            None,
            field_key,
            bounds[key],
            field=field,
        )

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_vm_plant_is_valid_changed(self) -> None:
        """Enable or disable the PSO run button based on plant validity."""
        self._btn_run_pso.setEnabled(self._vm_plant.is_valid)

    def _on_vm_pso_progress_changed(self, iteration: int) -> None:
        """Update the progress bar based on PSO iteration."""
        percent = int((iteration / self._vm_pso.get_pos_iteration()) * 100)
        self._progress_bar.setValue(percent)

    def _on_btn_run_pso(self) -> None:
        """Start PSO simulation if the plant is valid."""
        if not self._vm_plant.is_valid:
            return

        self._btn_run_pso.setEnabled(False)
        self._btn_interrupt_pso.setEnabled(True)
        self._lbl_interrupt_status.setText("")
        self._progress_bar.setValue(0)
        self._vm_pso.run_pso_simulation()

    def _on_btn_interrupt_pso(self) -> None:
        """Interrupt the running PSO simulation."""
        self._btn_interrupt_pso.setEnabled(False)
        self._btn_run_pso.setEnabled(self._vm_plant.is_valid)
        self._vm_pso.interrupt_pso_simulation()

    def _on_txt_changed(self, value: str | None = None, **kwargs: Any) -> None:
        """Handle user changes in QLineEdit field."""
        field = kwargs.get("field")
        if not isinstance(field, QLineEdit) or field is None:
            raise TypeError(f"Expected QObject, got {type(field)}")

        setter = kwargs.get("setter")
        if not isinstance(setter, Callable) or setter is None:
            raise TypeError(f"Expected Callable, got {type(setter)}")

        key = kwargs.get("key")
        if not isinstance(key, str) or key is None:
            raise TypeError(f"Expected str, got {type(key)}")

        if value is None:
            value = field.text()

        self._clear_input_error(field)
        self.logger.debug(f"UI event: txt_change changed (value={value})")
        setter(key, float(value))

    # ============================================================
    # Internal helpers
    # ============================================================
    def _set_formula_tf(self) -> None:
        """Update the plant transfer function formula display."""
        self.field_widgets[PsoField.PLANT_TF].set_formula(r"G(s) = " + self._vm_plant.get_current_tf())

    def _set_formula_function(self) -> None:
        """Update the excitation function formula display."""
        self.field_widgets[PsoField.FUNCTION_FORMULA].set_formula(self._vm_function.selected_function.get_formula())

    def _rebuild_pso_bounds_fields(self) -> None:
        self._frm_pso_bounds.clear_layout()

        for key in list(self.field_widgets.keys()):
            if PsoField.PSO_BOUNDS_KEY.value in key:
                del self.field_widgets[key]

        for key in list(self.labels.keys()):
            if PsoField.PSO_BOUNDS_KEY.value in key:
                del self.labels[key]

        self._frm_pso_bounds.add_layout(self._create_grid(self._get_pso_bounds_sections(), columns=2))

    def _get_pso_bounds_sections(self) -> list[SectionConfig]:
        fields = []
        for key in self._vm_controller.controller_spec.param_names:
            fields.append(
                SectionConfig(f"{key}.{PsoField.PSO_BOUNDS_KEY.value}", [
                    FieldConfig(
                        f"{key}.{PsoField.PSO_UPPER_KEY.value}.{PsoField.PSO_BOUNDS_KEY.value}",
                        QLineEdit,
                        validator=QDoubleValidator(0.0, 1e9, 6)
                    ),
                    FieldConfig(
                        f"{key}.{PsoField.PSO_LOWER_KEY.value}.{PsoField.PSO_BOUNDS_KEY.value}",
                        QLineEdit,
                        validator=QDoubleValidator(0.0, 1e9, 6)
                    )
                ])
            )
        return fields

    def _get_pso_bounds_widget_bindings(self) -> list[ConnectSignalConfig]:
        configs = []

        for key, field in self.field_widgets.items():
            if PsoField.PSO_BOUNDS_KEY.value not in key:
                continue

            setter: Callable[[str, float], None] | None = None
            if PsoField.PSO_LOWER_KEY.value in key:
                setter = self._vm_pso.set_lower_bound
            elif PsoField.PSO_UPPER_KEY.value in key:
                setter = self._vm_pso.set_upper_bound

            if setter is None:
                continue

            configs.append(
                ConnectSignalConfig(
                    key=key,
                    signal_name="editingFinished",
                    attr_name="",
                    widget=field,
                    kwargs={
                        "field": field,
                        "key": str(key.split('.')[0]),
                        "setter": lambda k, value, current_setter=setter: current_setter(k, value),
                    },
                    override_event_handler=self._on_txt_changed,
                )
            )

        return configs

    def _on_field_toggle_changed(self, checked: bool) -> None:
        """Handle gain margin toggle state changes."""
        self._vm_pso.gain_margin_enabled = checked

    def _sync_toggle_states(self) -> None:
        """Sync toggle widgets with the ViewModel's enabled state."""
        for config in self._get_toggle_vm_bindings():
            self._on_vm_field_enabled_changed(**config.kwargs)
        self._on_vm_overshoot_control_visibility_changed()

    def _apply_tool_tip_error_criterion(self) -> None:
        """Apply the tool tip."""
        field = self.field_widgets[PsoField.ERROR_CRITERION]
        tooltip = get_performance_tooltip(self._vm_pso.error_criterion)
        field.setToolTip(self._enum_translation(tooltip))

    def _get_widget_bindings(self) -> list[ConnectSignalConfig]:
        k_excitation_target = PsoField.EXCITATION_TARGET
        k_error_criterion = PsoField.ERROR_CRITERION
        k_t0 = PsoField.T0
        k_t1 = PsoField.T1
        k_overshoot_control = PsoField.OVERSHOOT_CONTROL
        k_slew_rate_max = PsoField.SLEW_RATE_MAX
        k_slew_window_size = PsoField.SLEW_WINDOW_SIZE
        k_gain_margin = PsoField.GAIN_MARGIN
        k_phase_margin = PsoField.PHASE_MARGIN
        k_stability_margin = PsoField.STABILITY_MARGIN
        k_slew_rate_limiter = PsoField.SLEW_RATE_LIMITER

        return [
            # Widget → VM signals
            ConnectSignalConfig(
                key=k_excitation_target,
                signal_name="currentIndexChanged",
                attr_name="_vm_pso.excitation_target",
                widget=self.field_widgets.get(k_excitation_target),
                kwargs={"value_type": ExcitationTarget},
                main_event_handler=self._on_widget_changed,
                post_event_handler=self._vm_pso.check_overshoot_control_visibility
            ),
            ConnectSignalConfig(
                key=k_error_criterion,
                signal_name="currentIndexChanged",
                attr_name="_vm_pso.error_criterion",
                widget=self.field_widgets.get(k_error_criterion),
                kwargs={"value_type": PerformanceIndex},
                main_event_handler=self._on_widget_changed,
                post_event_handler=self._apply_tool_tip_error_criterion
            ),
            ConnectSignalConfig(
                key=k_t0,
                signal_name="editingFinished",
                attr_name="_vm_pso.t0",
                widget=self.field_widgets.get(k_t0),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_t1,
                signal_name="editingFinished",
                attr_name="_vm_pso.t1",
                widget=self.field_widgets.get(k_t1),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_overshoot_control,
                signal_name="editingFinished",
                attr_name="_vm_pso.overshoot_control",
                widget=self.field_widgets.get(k_overshoot_control),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_slew_rate_max,
                signal_name="editingFinished",
                attr_name="_vm_pso.slew_rate_max",
                widget=self.field_widgets.get(k_slew_rate_max),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_slew_window_size,
                signal_name="editingFinished",
                attr_name="_vm_pso.slew_window_size",
                widget=self.field_widgets.get(k_slew_window_size),
                kwargs={"value_type": int},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_gain_margin,
                signal_name="editingFinished",
                attr_name="_vm_pso.gain_margin",
                widget=self.field_widgets.get(k_gain_margin),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_phase_margin,
                signal_name="editingFinished",
                attr_name="_vm_pso.phase_margin",
                widget=self.field_widgets.get(k_phase_margin),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_stability_margin,
                signal_name="editingFinished",
                attr_name="_vm_pso.stability_margin",
                widget=self.field_widgets.get(k_stability_margin),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),

            # Toggle / Enabled signals
            ConnectSignalConfig(
                key=k_overshoot_control,
                signal_name="toggled",
                attr_name="_vm_pso.overshoot_control_enabled",
                widget=self.labels.get(k_overshoot_control),
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_slew_rate_limiter,
                signal_name="activeChanged",
                attr_name="_vm_pso.slew_rate_limit_enabled",
                widget=self.labels.get(k_slew_rate_limiter),
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_gain_margin,
                signal_name="toggled",
                attr_name="_vm_pso.gain_margin_enabled",
                widget=self.labels.get(k_gain_margin),
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_phase_margin,
                signal_name="toggled",
                attr_name="_vm_pso.phase_margin_enabled",
                widget=self.labels.get(k_phase_margin),
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_stability_margin,
                signal_name="toggled",
                attr_name="_vm_pso.stability_margin_enabled",
                widget=self.labels.get(k_stability_margin),
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            ),
        ]

    def _get_vm_bindings(self) -> list[ConnectSignalConfig]:
        k_t0 = PsoField.T0
        k_t1 = PsoField.T1
        k_excitation_target = PsoField.EXCITATION_TARGET
        k_error_criterion = PsoField.ERROR_CRITERION
        k_overshoot_control = PsoField.OVERSHOOT_CONTROL
        k_slew_rate_max = PsoField.SLEW_RATE_MAX
        k_slew_window_size = PsoField.SLEW_WINDOW_SIZE
        k_gain_margin = PsoField.GAIN_MARGIN
        k_phase_margin = PsoField.PHASE_MARGIN
        k_stability_margin = PsoField.STABILITY_MARGIN

        return [
            ConnectSignalConfig(
                key=k_t0,
                signal_name="t0Changed",
                attr_name="t0",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_t0)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_t1,
                signal_name="t1Changed",
                attr_name="t1",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_t1)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_excitation_target,
                signal_name="excitationTargetChanged",
                attr_name="excitation_target",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_excitation_target)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_error_criterion,
                signal_name="performanceIndexChanged",
                attr_name="error_criterion",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_error_criterion)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_overshoot_control,
                signal_name="overshootControlChanged",
                attr_name="overshoot_control",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_overshoot_control)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_slew_rate_max,
                signal_name="slewRateMaxChanged",
                attr_name="slew_rate_max",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_slew_rate_max)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_slew_window_size,
                signal_name="slewWindowSizeChanged",
                attr_name="slew_window_size",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_slew_window_size)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_gain_margin,
                signal_name="gainMarginChanged",
                attr_name="gain_margin",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_gain_margin)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_phase_margin,
                signal_name="phaseMarginChanged",
                attr_name="phase_margin",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_phase_margin)},
                main_event_handler=self._on_vm_changed,
            ),
            ConnectSignalConfig(
                key=k_stability_margin,
                signal_name="stabilityMarginChanged",
                attr_name="stability_margin",
                widget=self._vm_pso,
                kwargs={"field": self.field_widgets.get(k_stability_margin)},
                main_event_handler=self._on_vm_changed,
            ),
        ]

    def _get_pso_bounds_vm_bindings(self) -> list[ConnectSignalConfig]:
        return [
            ConnectSignalConfig(
                key="",
                signal_name="lowerBoundsChanged",
                attr_name="",
                widget=self._vm_pso,
                kwargs={"bound_key": PsoField.PSO_LOWER_KEY.value},
                override_event_handler=self._on_vm_pso_bounds_changed,
            ),
            ConnectSignalConfig(
                key="",
                signal_name="upperBoundsChanged",
                attr_name="",
                widget=self._vm_pso,
                kwargs={"bound_key": PsoField.PSO_UPPER_KEY.value},
                override_event_handler=self._on_vm_pso_bounds_changed,
            ),
        ]

    def _get_toggle_vm_bindings(self) -> list[ConnectSignalConfig]:
        k_overshoot_control = PsoField.OVERSHOOT_CONTROL
        k_slew_rate_limiter = PsoField.SLEW_RATE_LIMITER
        k_gain_margin = PsoField.GAIN_MARGIN
        k_phase_margin = PsoField.PHASE_MARGIN
        k_stability_margin = PsoField.STABILITY_MARGIN

        return [
            ConnectSignalConfig(
                key=k_overshoot_control,
                signal_name="overshootControlEnabledChanged",
                attr_name="overshoot_control_enabled",
                widget=self._vm_pso,
                kwargs={
                    "lable": self.labels.get(k_overshoot_control),
                    "field": self.field_widgets.get(k_overshoot_control),
                    "is_enabled": lambda: self._vm_pso.overshoot_control_enabled,
                },
                override_event_handler=self._on_vm_field_enabled_changed,
            ),
            ConnectSignalConfig(
                key=k_slew_rate_limiter,
                signal_name="slewRateLimitEnabledChanged",
                attr_name="slew_rate_limit_enabled",
                widget=self._vm_pso,
                kwargs={
                    "lable": self.labels.get(k_slew_rate_limiter),
                    "is_enabled": lambda: self._vm_pso.slew_rate_limit_enabled,
                },
                override_event_handler=self._on_vm_field_enabled_changed
            ),
            ConnectSignalConfig(
                key=k_gain_margin,
                signal_name="gainMarginEnabledChanged",
                attr_name="gain_margin_enabled",
                widget=self._vm_pso,
                kwargs={
                    "lable": self.labels.get(k_gain_margin),
                    "field": self.field_widgets.get(k_gain_margin),
                    "is_enabled": lambda: self._vm_pso.gain_margin_enabled,
                },
                override_event_handler=self._on_vm_field_enabled_changed,
            ),
            ConnectSignalConfig(
                key=k_phase_margin,
                signal_name="phaseMarginEnabledChanged",
                attr_name="phase_margin_enabled",
                widget=self._vm_pso,
                kwargs={
                    "lable": self.labels.get(k_phase_margin),
                    "field": self.field_widgets.get(k_phase_margin),
                    "is_enabled": lambda: self._vm_pso.phase_margin_enabled,
                },
                override_event_handler=self._on_vm_field_enabled_changed,
            ),
            ConnectSignalConfig(
                key=k_stability_margin,
                signal_name="stabilityMarginEnabledChanged",
                attr_name="stability_margin_enabled",
                widget=self._vm_pso,
                kwargs={
                    "lable": self.labels.get(k_stability_margin),
                    "field": self.field_widgets.get(k_stability_margin),
                    "is_enabled": lambda: self._vm_pso.stability_margin_enabled,
                },
                override_event_handler=self._on_vm_field_enabled_changed,
            ),
        ]
