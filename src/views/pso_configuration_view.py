from functools import partial

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar
from PySide6.QtCore import QObject, Qt

from app_domain.ui_context import UiContext
from app_domain.controlsys import ExcitationTarget, PerformanceIndex
from utils import LatexRenderer
from viewmodels import PlantViewModel, FunctionViewModel, PsoConfigurationViewModel
from views import BaseView, FieldConfig, SectionConfig
from .translations import Translation


FIELDS: dict[str, list[FieldConfig | SectionConfig]] = {
    "excitation_target": [
        FieldConfig("excitation_target", QComboBox),
    ],
    "control": [
        SectionConfig("simulation_time", [
            FieldConfig("t0", QLineEdit),
            FieldConfig("t1", QLineEdit),
        ]),
        SectionConfig("performance_index", [
            FieldConfig("time_domain", QComboBox),
        ]),

        SectionConfig("pso_bounds_kp", [
            FieldConfig("kp_min", QLineEdit),
            FieldConfig("kp_max", QLineEdit),
        ]),
        SectionConfig("pso_bounds_ti", [
            FieldConfig("ti_min", QLineEdit),
            FieldConfig("ti_max", QLineEdit),
        ]),
        SectionConfig("pso_bounds_td", [
            FieldConfig("td_min", QLineEdit),
            FieldConfig("td_max", QLineEdit),
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

        main_layout.addWidget(self._create_plant_frame())
        main_layout.addWidget(self._create_function_frame())
        main_layout.addWidget(self._create_control_frame())
        main_layout.addWidget(self._create_run_pso_frame())
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_plant_frame(self) -> QFrame:
        frame, frame_layout = self._create_card()

        # Title
        self._lbl_title_plant = QLabel()
        self._apply_title_property(self._lbl_title_plant)
        frame_layout.addWidget(self._lbl_title_plant)

        # TF
        self._lbl_tf = QLabel()
        self._lbl_tf.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
        self._lbl_tf.setStyleSheet("background: transparent;")

        self._lbl_tf.setPixmap(
            LatexRenderer.latex2pixmap(
                r"G(s) = " + self._vm_plant.get_tf(),
                font_size_scale=self._formula_font_size_scale
            )
        )
        self._lbl_tf.setAlignment(Qt.AlignHCenter)  # type: ignore[attr-defined]

        frame_layout.addWidget(self._lbl_tf)

        return frame

    def _create_function_frame(self) -> QFrame:
        frame, frame_layout = self._create_card()

        # Title
        self._lbl_title_function = QLabel()
        self._apply_title_property(self._lbl_title_function)
        frame_layout.addWidget(self._lbl_title_function)

        frame_layout.addLayout(self._create_grid(FIELDS["excitation_target"], 4))

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
        frame, frame_layout = self._create_card()

        # Title
        self._lbl_title_control = QLabel()
        self._apply_title_property(self._lbl_title_control)
        frame_layout.addWidget(self._lbl_title_control)

        frame_layout.addLayout(self._create_grid(FIELDS["control"], 4))

        return frame

    def _create_run_pso_frame(self) -> QFrame:
        frame, frame_layout = self._create_card()

        # Title
        self._lbl_title_run_pso = QLabel()
        self._apply_title_property(self._lbl_title_run_pso)
        frame_layout.addWidget(self._lbl_title_run_pso)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setValue(0)
        frame_layout.addWidget(self._progress_bar)

        lbl_pso_result = QLabel()
        lbl_pso_result.setWordWrap(True)
        frame_layout.addWidget(lbl_pso_result)
        self._labels["pso_result"] = lbl_pso_result

        btn_run_pso = QPushButton()
        frame_layout.addWidget(btn_run_pso)
        self._labels["run_pso"] = btn_run_pso

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[str, tuple[str, str, object]] = {
            "t0": ("editingFinished", "_vm_pso.t0", float),
            "t1": ("editingFinished", "_vm_pso.t1", float),
            "excitation_target": ("currentIndexChanged", "_vm_pso.excitation_target", ExcitationTarget),
            "time_domain": ("currentIndexChanged", "_vm_pso.performance_index", PerformanceIndex),
            "kp_min": ("editingFinished", "_vm_pso.kp_min", float),
            "kp_max": ("editingFinished", "_vm_pso.kp_max", float),
            "ti_min": ("editingFinished", "_vm_pso.ti_min", float),
            "ti_max": ("editingFinished", "_vm_pso.ti_max", float),
            "td_min": ("editingFinished", "_vm_pso.td_min", float),
            "td_max": ("editingFinished", "_vm_pso.td_max", float),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self._widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

        self._labels["run_pso"].clicked.connect(self._on_btn_run_pso)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        # vm plant
        self._vm_plant.tfChanged.connect(self._on_vm_plant_tf_changed)
        self._vm_plant.isValidChanged.connect(self._on_vm_plant_is_valid_changed)
        # vm function
        self._vm_function.functionChanged.connect(self._on_vm_function_function_changed)
        # vm pso
        attributes: dict[str, tuple[str, str]] = {
            "t0": ("t0Changed", "_vm_pso.t0"),
            "t1": ("t1Changed", "_vm_pso.t1"),
            "excitation_target": ("excitationTargetChanged", "_vm_pso.excitation_target"),
            "time_domain": ("performanceIndexChanged", "_vm_pso.performance_index"),
            "kp_min": ("kpMinChanged", "_vm_pso.kp_min"),
            "kp_max": ("kpMaxChanged", "_vm_pso.kp_max"),
            "ti_min": ("tiMinChanged", "_vm_pso.ti_min"),
            "ti_max": ("tiMaxChanged", "_vm_pso.ti_max"),
            "td_min": ("tdMinChanged", "_vm_pso.td_min"),
            "td_max": ("tdMaxChanged", "_vm_pso.td_max"),
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
        self._lbl_title_plant.setText(self.tr("Plant"))
        self._lbl_title_function.setText(self.tr("Excitation Function"))
        self._lbl_title_control.setText(self.tr("Controller Optimization Parameters"))
        self._lbl_title_run_pso.setText(self.tr("PSO Simulation"))

        labels = {
            "simulation_time": self.tr("Simulation Time"),
            "t0": self.tr("Start Time"),
            "t1": self.tr("End Time"),
            "excitation_target": self.tr("Excitation Target"),
            "performance_index": self.tr("Performance Index"),
            "time_domain": self.tr("Time Domain"),
            "pso_bounds_kp": self.tr("PSO Bounds: Kp"),
            "kp_min": self.tr("Minimum"),
            "kp_max": self.tr("Maximum"),
            "pso_bounds_ti": self.tr("PSO Bounds: Ti"),
            "ti_min": self.tr("Minimum"),
            "ti_max": self.tr("Maximum"),
            "pso_bounds_td": self.tr("PSO Bounds: Td"),
            "td_min": self.tr("Minimum"),
            "td_max": self.tr("Maximum"),
            "run_pso": self.tr("Start PSO Simulation"),
        }

        for key in labels.keys():
            self._labels[key].setText(labels[key])

        translation = Translation()

        item_enums = {
            "excitation_target": translation(ExcitationTarget),
            "time_domain": translation(PerformanceIndex),
        }

        for key in item_enums:
            self._cmb_add_item(self._widgets[key], item_enums[key])

        self._lbl_pso_result_template = self.tr(
            "PSO Result:\n"
            "Time = %(time).2f s\n"
            "Kp   = %(kp).3f\n"
            "Ti   = %(ti).3f\n"
            "Td   = %(td).3f\n"
            "Tf   = %(tf).3f"
        )

        result = self._vm_pso.get_pso_result()
        if result is None:
            self._labels["pso_result"].setText("")

        else:
            self._labels["pso_result"].setText(self._lbl_pso_result_template % {
                "time": result.simulation_time,
                "kp": result.kp,
                "ti": result.ti,
                "td": result.td,
                "tf": result.tf
            })

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        keys = ["t0", "t1", "kp_min", "kp_max", "ti_min", "ti_max", "td_min", "td_max"]
        values = [
            self._vm_pso.t0,
            self._vm_pso.t1,
            self._vm_pso.kp_min,
            self._vm_pso.kp_max,
            self._vm_pso.ti_min,
            self._vm_pso.ti_max,
            self._vm_pso.td_min,
            self._vm_pso.td_max,
        ]
        for key, value in zip(keys, values):
            self._widgets[key].setText(f"{round(float(value), self._dec):.{self._dec}}")

        attributes: dict[str, str] = {
            "excitation_target": "excitation_target",
            "time_domain": "performance_index",
        }
        for key, attr in attributes.items():
            index = self._widgets[key].findData(getattr(self._vm_pso, attr))
            if index >= 0:
                self._widgets[key].setCurrentIndex(index)

        self._labels["run_pso"].setEnabled(self._vm_plant.is_valid)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_plant_tf_changed(self) -> None:
        self._lbl_tf.setPixmap(
            LatexRenderer.latex2pixmap(
                r"G(s) = " + self._vm_plant.get_tf(),
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
    def _on_vm_plant_is_valid_changed(self) -> None:
        self._labels["run_pso"].setEnabled(self._vm_plant.is_valid)

    def _on_vm_pso_progress_changed(self, iteration: int) -> None:
        percent = int((iteration / self._vm_pso.get_pos_iteration()) * 100)
        self._progress_bar.setValue(percent)

    def _on_btn_run_pso(self) -> None:
        if not self._vm_plant.is_valid:
            return

        self._labels["run_pso"].setEnabled(False)
        self._labels["pso_result"].setText("")
        self._progress_bar.setValue(0)
        self._vm_pso.run_pso_simulation()

    def _on_vm_pso_simulation_finished(self) -> None:
        self._labels["run_pso"].setEnabled(True)

        result = self._vm_pso.get_pso_result()
        if result is None:
            self._labels["pso_result"].setText("")
            return

        self._labels["pso_result"].setText(self._lbl_pso_result_template % {
            "time": result.simulation_time,
            "kp": result.kp,
            "ti": result.ti,
            "td": result.td,
            "tf": result.tf
        })
