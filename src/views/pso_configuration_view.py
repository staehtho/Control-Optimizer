from functools import partial

from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar, QHBoxLayout
from PySide6.QtCore import QObject, Qt

from app_domain.ui_context import UiContext
from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from viewmodels import PlantViewModel, FunctionViewModel, PsoConfigurationViewModel
from app_types import PsoField
from .base_view import BaseView, FieldConfig, SectionConfig
from views.widgets import SectionFrame, FormulaWidget
from .resources import Icons

FIELDS: dict[str, list[FieldConfig | SectionConfig]] = {
    "excitation_target": [
        FieldConfig(PsoField.EXCITATION_TARGET, QComboBox),
        FieldConfig(PsoField.FUNCTION_FORMULA, FormulaWidget),
    ],
    "control": [
        SectionConfig(PsoField.SIMULATION_TIME, [
            FieldConfig(PsoField.T0, QLineEdit),
            FieldConfig(PsoField.T1, QLineEdit),
        ]),
        SectionConfig(PsoField.PERFORMANCE_INDEX, [
            FieldConfig(PsoField.TIME_DOMAIN, QComboBox),
        ]),

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
    ]
}


class PsoConfigurationView(BaseView, QWidget):
    def __init__(self, ui_context: UiContext, vm_plant: PlantViewModel, vm_function: FunctionViewModel,
                 vm_pso: PsoConfigurationViewModel,
                 parent: QObject = None):
        QWidget.__init__(self, parent)

        self._vm_plant = vm_plant
        self._vm_function = vm_function
        self._vm_pso = vm_pso

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
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

        self._frm_plant = self._create_plant_frame()
        main_layout.addWidget(self._frm_plant)
        self._frm_function = self._create_function_frame()
        main_layout.addWidget(self._frm_function)
        self._frm_controller = self._create_controller_frame()
        main_layout.addWidget(self._frm_controller)
        self._frm_run_pso = self._create_run_pso_frame()
        main_layout.addWidget(self._frm_run_pso)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_plant_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, frame_layout = self._create_card(self)

        # TF
        self._lbl_tf = FormulaWidget(
            r"G(s) = " + self._vm_plant.get_tf(), self._formula_font_size_scale, parent=frame
        )
        self._lbl_tf.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        frame_layout.addWidget(self._lbl_tf)

        return frame

    def _create_function_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, frame_layout = self._create_card(self)

        frame_layout.addLayout(self._create_grid(FIELDS["excitation_target"], 4))

        widget: FormulaWidget = self._field_widgets[PsoField.FUNCTION_FORMULA]
        widget.set_font_size(self._formula_font_size_scale)
        widget.set_formula(self._vm_function.selected_function.get_formula())

        return frame

    def _create_controller_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, frame_layout = self._create_card(self)

        frame_layout.addLayout(self._create_grid(FIELDS["control"], 4))

        return frame

    def _create_run_pso_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, frame_layout = self._create_card(self)

        self._progress_bar = QProgressBar(frame)
        self._progress_bar.setMinimum(0)
        self._progress_bar.setValue(0)
        frame_layout.addWidget(self._progress_bar)

        btn_run_pso = QPushButton(frame)
        frame_layout.addWidget(btn_run_pso)
        self._labels[PsoField.RUN_PSO] = btn_run_pso

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[PsoField, tuple[str, str, object]] = {
            PsoField.T0: ("editingFinished", "_vm_pso.t0", float),
            PsoField.T1: ("editingFinished", "_vm_pso.t1", float),
            PsoField.EXCITATION_TARGET: ("currentIndexChanged", "_vm_pso.excitation_target", ExcitationTarget),
            PsoField.TIME_DOMAIN: ("currentIndexChanged", "_vm_pso.performance_index", PerformanceIndex),
            PsoField.KP_MIN: ("editingFinished", "_vm_pso.kp_min", float),
            PsoField.KP_MAX: ("editingFinished", "_vm_pso.kp_max", float),
            PsoField.TI_MIN: ("editingFinished", "_vm_pso.ti_min", float),
            PsoField.TI_MAX: ("editingFinished", "_vm_pso.ti_max", float),
            PsoField.TD_MIN: ("editingFinished", "_vm_pso.td_min", float),
            PsoField.TD_MAX: ("editingFinished", "_vm_pso.td_max", float),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self._field_widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

        self._labels[PsoField.RUN_PSO].clicked.connect(self._on_btn_run_pso)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # Plant ViewModel
        self._vm_plant.tfChanged.connect(self._on_vm_plant_tf_changed)
        self._vm_plant.isValidChanged.connect(self._on_vm_plant_is_valid_changed)
        # Function ViewModel
        self._vm_function.functionChanged.connect(self._on_vm_function_function_changed)
        # PSO Configuration ViewModel
        self._vm_pso.validationFailed.connect(self._on_validation_failed)
        attributes: dict[PsoField, tuple[str, str]] = {
            PsoField.T0: ("t0Changed", "_vm_pso.t0"),
            PsoField.T1: ("t1Changed", "_vm_pso.t1"),
            PsoField.EXCITATION_TARGET: ("excitationTargetChanged", "_vm_pso.excitation_target"),
            PsoField.TIME_DOMAIN: ("performanceIndexChanged", "_vm_pso.performance_index"),
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

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("PSO Parameter"))
        self._frm_plant.set_title(self.tr("Plant"))
        self._frm_function.set_title(self.tr("Excitation Function"))
        self._frm_controller.set_title(self.tr("Controller Optimization Parameters"))
        self._frm_run_pso.set_title(self.tr("PSO Simulation"))

        labels = {
            PsoField.SIMULATION_TIME: self.tr("Simulation Time"),
            PsoField.T0: self.tr("Start Time"),
            PsoField.T1: self.tr("End Time"),
            PsoField.EXCITATION_TARGET: self.tr("Excitation Target"),
            PsoField.FUNCTION_FORMULA: self.tr("Function"),
            PsoField.PERFORMANCE_INDEX: self.tr("Performance Index"),
            PsoField.TIME_DOMAIN: self.tr("Time Domain"),
            PsoField.KP_BOUNDS: self.tr("PSO Bounds: Kp"),
            PsoField.KP_MIN: self.tr("Minimum"),
            PsoField.KP_MAX: self.tr("Maximum"),
            PsoField.TI_BOUNDS: self.tr("PSO Bounds: Ti"),
            PsoField.TI_MIN: self.tr("Minimum"),
            PsoField.TI_MAX: self.tr("Maximum"),
            PsoField.TD_BOUNDS: self.tr("PSO Bounds: Td"),
            PsoField.TD_MIN: self.tr("Minimum"),
            PsoField.TD_MAX: self.tr("Maximum"),
            PsoField.RUN_PSO: self.tr("Start PSO Simulation"),
        }

        for key in labels.keys():
            self._labels[key].setText(labels[key])

        enums = {PsoField.EXCITATION_TARGET: ExcitationTarget, PsoField.TIME_DOMAIN: PerformanceIndex}
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self._field_widgets[key], data)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
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
            self._field_widgets[key].setText(f"{value}")

        attributes: dict[PsoField, str] = {
            PsoField.EXCITATION_TARGET: "excitation_target",
            PsoField.TIME_DOMAIN: "performance_index",
        }
        for key, attr in attributes.items():
            index = self._field_widgets[key].findData(getattr(self._vm_pso, attr))
            if index >= 0:
                self._field_widgets[key].setCurrentIndex(index)

        self._labels[PsoField.RUN_PSO].setEnabled(self._vm_plant.is_valid)

    # -------------------------------------------------
    # Applied theme
    # -------------------------------------------------
    def _on_theme_applied(self) -> None:
        icon = self._load_icon(Icons.pso_parameter, self._titel_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._titel_icon_size, self._titel_icon_size))

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_plant_tf_changed(self) -> None:
        self._lbl_tf.set_formula(r"G(s) = " + self._vm_plant.get_tf())

    def _on_vm_function_function_changed(self) -> None:
        self._field_widgets[PsoField.FUNCTION_FORMULA].set_formula(self._vm_function.selected_function.get_formula())

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_vm_plant_is_valid_changed(self) -> None:
        self._labels[PsoField.RUN_PSO].setEnabled(self._vm_plant.is_valid)

    def _on_vm_pso_progress_changed(self, iteration: int) -> None:
        percent = int((iteration / self._vm_pso.get_pos_iteration()) * 100)
        self._progress_bar.setValue(percent)

    def _on_btn_run_pso(self) -> None:
        if not self._vm_plant.is_valid:
            return

        self._labels[PsoField.RUN_PSO].setEnabled(False)
        self._progress_bar.setValue(0)
        self._vm_pso.run_pso_simulation()

    def _on_vm_pso_simulation_finished(self) -> None:
        self._labels[PsoField.RUN_PSO].setEnabled(True)
