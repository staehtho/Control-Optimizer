from functools import partial

from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QVBoxLayout, QFrame, QLineEdit

from app_domain.ui_context import UiContext
from app_domain.controlsys import AntiWindup
from viewmodels import ControllerViewModel
from views import BaseView, FieldConfig, SectionConfig
from .translations import Translation

FIELDS: list[FieldConfig] = [
    SectionConfig("constraint", [
        FieldConfig("constraint_min", QLineEdit),
        FieldConfig("constraint_max", QLineEdit),
    ]),

    FieldConfig("controller_type", QLabel),
    FieldConfig("anti_windup", QComboBox),
]


class ControllerView(BaseView, QWidget):
    def __init__(self, ui_context: UiContext, vm_controller: ControllerViewModel, parent: QWidget = None):
        QWidget.__init__(self, parent)

        self._vm_controller = vm_controller

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        main_layout.addWidget(self._create_controller_frame())
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_controller_frame(self) -> QFrame:
        frame, frame_layout = self._create_card()

        # Title
        self._lbl_title_controller = QLabel()
        self._apply_title_property(self._lbl_title_controller)
        frame_layout.addWidget(self._lbl_title_controller)
        frame_layout.addLayout(self._create_grid(FIELDS))

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[str, tuple[str, str, object]] = {
            "constraint_min": ("editingFinished", "_vm_controller.constraint_min", float),
            "constraint_max": ("editingFinished", "_vm_controller.constraint_max", float),
            "anti_windup": ("currentIndexChanged", "_vm_controller.anti_windup", AntiWindup),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self._widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_controller.constraintMinChanged.connect(
            partial(self._on_vm_changed, "constraint_min", "_vm_controller.constraint_min")
        )
        self._vm_controller.constraintMaxChanged.connect(
            partial(self._on_vm_changed, "constraint_max", "_vm_controller.constraint_max")
        )
        self._vm_controller.antiWindupChanged.connect(
            partial(self._on_vm_changed, "anti_windup", "_vm_controller.anti_windup")
        )

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title_controller.setText(self.tr("Controller"))

        labels = {
            "controller_type": self.tr("Controller Type"),
            "anti_windup": self.tr("Anti Windup"),
            "constraint": self.tr("Constraint"),
            "constraint_min": self.tr("Minimum"),
            "constraint_max": self.tr("Maximum"),
        }

        for key in labels.keys():
            self._labels[key].setText(labels[key])

        translation = Translation()
        self._cmb_add_item(self._widgets["anti_windup"], translation(AntiWindup))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._widgets["controller_type"].setText(self._vm_controller.controller_type)

        index = self._widgets["anti_windup"].findData(self._vm_controller.anti_windup)
        if index >= 0:
            self._widgets["anti_windup"].setCurrentIndex(index)

        self._widgets["constraint_min"].setText(f"{self._vm_controller.constraint_min:.{self._dec}}")
        self._widgets["constraint_max"].setText(f"{self._vm_controller.constraint_max:.{self._dec}}")
