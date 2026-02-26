from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QLineEdit, QComboBox
from PySide6.QtCore import QObject, Qt


from app_domain.controlsys import AntiWindup, ExcitationTarget, PerformanceIndex
from utils import LatexRenderer
from viewmodels import LanguageViewModel, PlantViewModel, FunctionViewModel, PsoConfigurationViewModel
from views import BaseView, FieldConfig, SectionConfig
from .translations import Translation


FIELDS: dict[str, list[FieldConfig | SectionConfig]] = {
    "control": [
        FieldConfig("excitation_target", QComboBox),
        FieldConfig("performance_index", QComboBox),
        SectionConfig("simulation_time", [
            FieldConfig("start_time", QLineEdit),
            FieldConfig("end_time", QLineEdit),
        ]),

        SectionConfig("constraint", [
            FieldConfig("constraint_min", QLineEdit),
            FieldConfig("constraint_max", QLineEdit),
        ]),
    ],
    "pso": [
        SectionConfig("kp", [
            FieldConfig("kp_min", QLineEdit),
            FieldConfig("kp_max", QLineEdit),
        ]),
        SectionConfig("ti", [
            FieldConfig("ti_min", QLineEdit),
            FieldConfig("ti_max", QLineEdit),
        ]),
        SectionConfig("td", [
            FieldConfig("td_min", QLineEdit),
            FieldConfig("td_max", QLineEdit),
        ]),
    ]
}


class PsoConfigurationView(BaseView, QWidget):
    def __init__(self, vm_lang: LanguageViewModel, vm_plant: PlantViewModel, vm_function: FunctionViewModel, vm_pso: PsoConfigurationViewModel,
                 parent: QObject = None):
        QWidget.__init__(self, parent)

        self._vm_plant = vm_plant
        self._vm_function = vm_function
        self._vm_pso = vm_pso

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = QVBoxLayout()

        main_layout.addWidget(self._create_plant_frame())
        main_layout.addWidget(self._create_function_frame())
        main_layout.addWidget(self._create_control_frame())
        main_layout.addWidget(self._create_pso_frame())

        self.setLayout(main_layout)

    def _create_plant_frame(self) -> QFrame:

        plant_frame = QFrame()
        plant_frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        plant_frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        plant_frame_layout = QVBoxLayout(plant_frame)

        # Title
        self._lbl_title_plant = QLabel()
        self._apply_title_property(self._lbl_title_plant)
        plant_frame_layout.addWidget(self._lbl_title_plant)

        # TF
        self._lbl_tf = QLabel()
        self._lbl_tf.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
        self._lbl_tf.setStyleSheet("background: transparent;")

        self._lbl_tf.setPixmap(
            LatexRenderer.latex2pixmap(
                self._vm_plant.get_formula(),
                font_size_scale=self._formula_font_size_scale
            )
        )
        self._lbl_tf.setAlignment(Qt.AlignHCenter)  # type: ignore[attr-defined]

        plant_frame_layout.addWidget(self._lbl_tf)

        return plant_frame

    def _create_function_frame(self) -> QFrame:

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_function = QLabel()
        self._apply_title_property(self._lbl_title_function)
        frame_layout.addWidget(self._lbl_title_function)

        self._lbl_function = QLabel()
        self._lbl_function.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
        self._lbl_function.setStyleSheet("background: transparent;")

        self._lbl_function.setPixmap(
            LatexRenderer.latex2pixmap(
                self._vm_function.selected_function.get_formula(),
                font_size_scale=self._formula_font_size_scale
            )
        )
        self._lbl_function.setAlignment(Qt.AlignHCenter)  # type: ignore[attr-defined]

        frame_layout.addWidget(self._lbl_function)

        return frame

    def _create_control_frame(self) -> QFrame:

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_control = QLabel()
        self._apply_title_property(self._lbl_title_control)
        frame_layout.addWidget(self._lbl_title_control)

        frame_layout.addLayout(self._create_grid(FIELDS["control"], 4))

        return frame

    def _create_pso_frame(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)  # type: ignore[attr-defined]
        frame.setFrameShadow(QFrame.Raised)  # type: ignore[attr-defined]

        frame_layout = QVBoxLayout(frame)

        # Title
        self._lbl_title_pso = QLabel()
        self._apply_title_property(self._lbl_title_pso)
        frame_layout.addWidget(self._lbl_title_pso)

        frame_layout.addLayout(self._create_grid(FIELDS["pso"], 4))

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        ...

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_plant.tfChanged.connect(self._on_vm_plant_tf_changed)
        self._vm_function.functionChanged.connect(self._on_vm_function_function_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title_plant.setText(self.tr("Plant"))
        self._lbl_title_control.setText(self.tr("Controller Optimization Parameters"))
        self._lbl_title_pso.setText(self.tr("PSO Bounds"))
        self._lbl_title_function.setText(self.tr("Excitation Function"))

        labels = {
            "simulation_time": self.tr("Simulation Time"),
            "start_time": self.tr("Start Time"),
            "end_time": self.tr("End Time"),
            "excitation_target": self.tr("Excitation Target"),
            "performance_index": self.tr("Performance Index"),
            "constraint": self.tr("Constraint"),
            "constraint_min": self.tr("Minimum"),
            "constraint_max": self.tr("Maximum"),
            "kp": self.tr("Kp"),
            "kp_min": self.tr("Minimum"),
            "kp_max": self.tr("Maximum"),
            "ti": self.tr("Ti"),
            "ti_min": self.tr("Minimum"),
            "ti_max": self.tr("Maximum"),
            "td": self.tr("Td"),
            "td_min": self.tr("Minimum"),
            "td_max": self.tr("Maximum"),
        }

        for key in labels.keys():
            self._labels[key].setText(labels[key])

        translation = Translation()

        item_enums = {
            "excitation_target": translation(ExcitationTarget),
            "performance_index": translation(PerformanceIndex),
        }

        for key in item_enums:
            self._cmb_add_item(self._widgets[key], item_enums[key])

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        ...

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_plant_tf_changed(self) -> None:
        self._lbl_tf.setPixmap(
            LatexRenderer.latex2pixmap(
                self._vm_plant.get_formula(),
                font_size_scale=self._formula_font_size_scale
            )
        )

    def _on_vm_function_function_changed(self) -> None:
        self._lbl_function.setPixmap(
            LatexRenderer.latex2pixmap(
                self._vm_function.selected_function.get_formula(),
                font_size_scale=self._formula_font_size_scale
            )
        )

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
