from functools import partial

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QProgressBar,
    QHBoxLayout,
    QSizePolicy,
    QLayout,
)
from PySide6.QtCore import QObject

from app_domain.ui_context import UiContext
from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from app_types import PsoField, FieldConfig, SectionConfig
from viewmodels import PlantViewModel, FunctionViewModel, PsoConfigurationViewModel
from views.view_mixin import ViewMixin
from views.widgets import SectionFrame, FormulaWidget
from views.resources import Icons

FIELDS: list[FieldConfig | SectionConfig] = [
    SectionConfig(PsoField.PLANT, [
        FieldConfig(PsoField.PLANT_TF, FormulaWidget, False),
        FieldConfig("", QLabel, False),
    ]),
    SectionConfig(PsoField.EXCITATION, [
        FieldConfig(PsoField.FUNCTION_FORMULA, FormulaWidget, False),
        FieldConfig(PsoField.EXCITATION_TARGET, QComboBox),
    ]),
    SectionConfig(PsoField.SIMULATION_TIME, [
        FieldConfig(PsoField.T0, QLineEdit),
        FieldConfig(PsoField.T1, QLineEdit),
    ]),
    SectionConfig(PsoField.PSO_BOUNDS, [
        SectionConfig(PsoField.KP_BOUNDS, [
            FieldConfig(PsoField.KP_MIN, QLineEdit),
            FieldConfig(PsoField.KP_MAX, QLineEdit),
        ]),
        SectionConfig(PsoField.TI_BOUNDS, [
            FieldConfig(PsoField.TI_MIN, QLineEdit),
            FieldConfig(PsoField.TI_MAX, QLineEdit),
        ]),
        SectionConfig(PsoField.TD_BOUNDS, [
            FieldConfig(PsoField.TD_MIN, QLineEdit),
            FieldConfig(PsoField.TD_MAX, QLineEdit),
        ]),
    ]),
    SectionConfig(PsoField.PERFORMANCE_INDEX, [
        SectionConfig(PsoField.TIME_DOMAIN, [
            FieldConfig(PsoField.ERROR_CRITERION, QComboBox),
        ]),
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
            vm_pso: PsoConfigurationViewModel,
            parent: QObject = None,
    ):
        QWidget.__init__(self, parent)

        self._vm_plant = vm_plant
        self._vm_function = vm_function
        self._vm_pso = vm_pso

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.pso_parameter, self._titel_icon_size)
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

        main_layout.addLayout(self._create_field_grid())

        self._frm_run_pso = self._create_run_pso_frame()
        main_layout.addWidget(self._frm_run_pso)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_field_grid(self) -> QLayout:

        grid = self._create_grid(FIELDS)

        self.field_widgets[PsoField.PLANT_TF].set_font_size(self._formula_font_size_scale)
        self.field_widgets[PsoField.FUNCTION_FORMULA].set_font_size(self._formula_font_size_scale)

        return grid

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

        self._btn_run_pso = QPushButton(frame)
        self._btn_run_pso.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_layout.addWidget(self._btn_run_pso)
        self.labels[PsoField.RUN_PSO] = self._btn_run_pso

        self._btn_interrupt_pso = QPushButton(frame)
        self._btn_interrupt_pso.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_interrupt_pso.setEnabled(False)
        btn_layout.addWidget(self._btn_interrupt_pso)
        self.labels[PsoField.INTERRUPT_PSO] = self._btn_interrupt_pso

        self._lbl_interrupt_status = QLabel(frame)
        self._lbl_interrupt_status.setObjectName("statusText")
        self._lbl_interrupt_status.setText("")
        btn_layout.addWidget(self._lbl_interrupt_status)

        btn_layout.addStretch()
        frame_layout.addLayout(btn_layout)

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[PsoField, tuple[str, str, object]] = {
            PsoField.EXCITATION_TARGET: ("currentIndexChanged", "_vm_pso.excitation_target", ExcitationTarget),
            PsoField.ERROR_CRITERION: ("currentIndexChanged", "_vm_pso.error_criterion", PerformanceIndex),
            PsoField.KP_MIN: ("editingFinished", "_vm_pso.kp_min", float),
            PsoField.KP_MAX: ("editingFinished", "_vm_pso.kp_max", float),
            PsoField.TI_MIN: ("editingFinished", "_vm_pso.ti_min", float),
            PsoField.TI_MAX: ("editingFinished", "_vm_pso.ti_max", float),
            PsoField.TD_MIN: ("editingFinished", "_vm_pso.td_min", float),
            PsoField.TD_MAX: ("editingFinished", "_vm_pso.td_max", float),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self.field_widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

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
        # PSO Configuration ViewModel
        self._vm_pso.validationFailed.connect(self._on_validation_failed)
        attributes: dict[PsoField, tuple[str, str]] = {
            PsoField.T0: ("t0Changed", "_vm_pso.t0"),
            PsoField.T1: ("t1Changed", "_vm_pso.t1"),
            PsoField.EXCITATION_TARGET: ("excitationTargetChanged", "_vm_pso.excitation_target"),
            PsoField.ERROR_CRITERION: ("performanceIndexChanged", "_vm_pso.error_criterion"),
            PsoField.KP_MIN: ("kpMinChanged", "_vm_pso.kp_min"),
            PsoField.KP_MAX: ("kpMaxChanged", "_vm_pso.kp_max"),
            PsoField.TI_MIN: ("tiMinChanged", "_vm_pso.ti_min"),
            PsoField.TI_MAX: ("tiMaxChanged", "_vm_pso.ti_max"),
            PsoField.TD_MIN: ("tdMinChanged", "_vm_pso.td_min"),
            PsoField.TD_MAX: ("tdMaxChanged", "_vm_pso.td_max"),
        }
        for key, value in attributes.items():
            signal, attr = value
            getattr(self._vm_pso, signal).connect(
                partial(self._on_vm_changed, key, attr)
            )

        self._vm_pso.psoProgressChanged.connect(self._on_vm_pso_progress_changed)
        self._vm_pso.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)
        self._vm_pso.psoSimulationInterrupted.connect(self._on_vm_pso_simulation_interrupted)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("PSO Parameter"))
        self._frm_run_pso.setText(self.tr("PSO Simulation"))

        labels = {
            PsoField.PLANT: self.tr("Plant"),
            PsoField.EXCITATION: self.tr("Excitation Function"),
            PsoField.EXCITATION_TARGET: self.tr("Excitation Target"),
            PsoField.SIMULATION_TIME: self.tr("Simulation Time"),
            PsoField.T0: self.tr("Start Time"),
            PsoField.T1: self.tr("End Time"),
            PsoField.PERFORMANCE_INDEX: self.tr("Performance Index"),
            PsoField.TIME_DOMAIN: self.tr("Time Domain"),
            PsoField.ERROR_CRITERION: self.tr("Error Criterion"),
            PsoField.PSO_BOUNDS: self.tr("PSO Bounds"),
            PsoField.KP_BOUNDS: self.tr("Kp Bounds"),
            PsoField.KP_MIN: self.tr("Minimum"),
            PsoField.KP_MAX: self.tr("Maximum"),
            PsoField.TI_BOUNDS: self.tr("Ti Bounds"),
            PsoField.TI_MIN: self.tr("Minimum"),
            PsoField.TI_MAX: self.tr("Maximum"),
            PsoField.TD_BOUNDS: self.tr("Td Bounds"),
            PsoField.TD_MIN: self.tr("Minimum"),
            PsoField.TD_MAX: self.tr("Maximum"),
            PsoField.RUN_PSO: self.tr("Start PSO Simulation"),
            PsoField.INTERRUPT_PSO: self.tr("Interrupt"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        enums = {PsoField.EXCITATION_TARGET: ExcitationTarget, PsoField.ERROR_CRITERION: PerformanceIndex}
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self.field_widgets[key], data)

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            PsoField.T0: self._vm_pso.t0,
            PsoField.T1: self._vm_pso.t1,
            PsoField.KP_MIN: self._vm_pso.kp_min,
            PsoField.KP_MAX: self._vm_pso.kp_max,
            PsoField.TI_MIN: self._vm_pso.ti_min,
            PsoField.TI_MAX: self._vm_pso.ti_max,
            PsoField.TD_MIN: self._vm_pso.td_min,
            PsoField.TD_MAX: self._vm_pso.td_max,

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

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.pso_parameter, self._titel_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._titel_icon_size, self._titel_icon_size))

        self._set_formula_tf()
        self._set_formula_function()

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_vm_plant_tf_changed(self) -> None:
        """Update the plant transfer function formula when it changes."""
        self._set_formula_tf()

    def _on_vm_function_function_changed(self) -> None:
        """Update the excitation function formula when it changes."""
        self._set_formula_function()

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

    def _on_vm_pso_simulation_finished(self) -> None:
        """Re-enable the run button after PSO simulation completes."""
        self._btn_run_pso.setEnabled(True)
        self._btn_interrupt_pso.setEnabled(False)

    def _on_vm_pso_simulation_interrupted(self) -> None:
        """Re-enable the run button after PSO simulation interruption."""
        self._btn_run_pso.setEnabled(self._vm_plant.is_valid)
        self._btn_interrupt_pso.setEnabled(False)
        self._lbl_interrupt_status.setText(self.tr("Interrupted"))

    # ============================================================
    # Internal helpers
    # ============================================================
    def _set_formula_tf(self) -> None:
        """Update the plant transfer function formula display."""
        self.field_widgets[PsoField.PLANT_TF].set_formula(r"G(s) = " + self._vm_plant.get_current_tf())

    def _set_formula_function(self) -> None:
        """Update the excitation function formula display."""
        self.field_widgets[PsoField.FUNCTION_FORMULA].set_formula(self._vm_function.selected_function.get_formula())
