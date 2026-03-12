from functools import partial
from pathlib import Path

from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QLineEdit

from app_domain.ui_context import UiContext
from app_domain.controlsys import AntiWindup
from utils import recolor_svg
from viewmodels import ControllerViewModel
from app_types import ControllerField
from .base_view import BaseView, FieldConfig, SectionConfig
from views.widgets import ExpandableFrame, AspectRatioSvgWidget

FIELDS: list[FieldConfig] = [
    SectionConfig(ControllerField.CONSTRAINT, [
        FieldConfig(ControllerField.CONSTRAINT_MIN, QLineEdit),
        FieldConfig(ControllerField.CONSTRAINT_MAX, QLineEdit),
    ]),

    FieldConfig(ControllerField.CONTROLLER_TYPE, QLabel),
    FieldConfig(ControllerField.ANTI_WINDUP, QComboBox),
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

        self._lbl_title = QLabel(self)
        self._lbl_title.setObjectName("viewTitle")
        main_layout.addWidget(self._lbl_title)

        self._frm_controller = self._create_controller_frame()
        main_layout.addWidget(self._frm_controller)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_controller_frame(self) -> ExpandableFrame:
        frame: ExpandableFrame
        frame, frame_layout = self._create_card(self)

        frame_layout.addLayout(self._create_grid(FIELDS))

        svg_path = Path("resources/pid_controller_block_diagram.svg")
        svg_text = svg_path.read_text(encoding="utf-8")
        recolored = recolor_svg(svg_text, self._vm_theme.get_svg_color_map())

        svg_widget = AspectRatioSvgWidget(svg_bytes=recolored.encode("utf-8"), initial_scale=2)
        frame_layout.addWidget(svg_widget)

        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[ControllerField, tuple[str, str, object]] = {
            ControllerField.CONSTRAINT_MIN: ("editingFinished", "_vm_controller.constraint_min", float),
            ControllerField.CONSTRAINT_MAX: ("editingFinished", "_vm_controller.constraint_max", float),
            ControllerField.ANTI_WINDUP: ("currentIndexChanged", "_vm_controller.anti_windup", AntiWindup),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self._field_widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_controller.validationFailed.connect(self._on_validation_failed)
        self._vm_controller.constraintMinChanged.connect(
            partial(self._on_vm_changed, ControllerField.CONSTRAINT_MIN, "_vm_controller.constraint_min")
        )
        self._vm_controller.constraintMaxChanged.connect(
            partial(self._on_vm_changed, ControllerField.CONSTRAINT_MAX, "_vm_controller.constraint_max")
        )
        self._vm_controller.antiWindupChanged.connect(
            partial(self._on_vm_changed, ControllerField.ANTI_WINDUP, "_vm_controller.anti_windup")
        )

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Controller"))
        self._frm_controller.set_title(self.tr("Parameters"))

        labels = {
            ControllerField.CONTROLLER_TYPE: self.tr("Controller Type"),
            ControllerField.ANTI_WINDUP: self.tr("Anti Windup"),
            ControllerField.CONSTRAINT: self.tr("Constraint"),
            ControllerField.CONSTRAINT_MIN: self.tr("Minimum"),
            ControllerField.CONSTRAINT_MAX: self.tr("Maximum"),
        }

        for key in labels.keys():
            self._labels[key].setText(labels[key])

        enums = {ControllerField.ANTI_WINDUP: AntiWindup}
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self._field_widgets[key], data)

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._field_widgets[ControllerField.CONTROLLER_TYPE].setText(self._vm_controller.controller_type)

        index = self._field_widgets[ControllerField.ANTI_WINDUP].findData(self._vm_controller.anti_windup)
        if index >= 0:
            self._field_widgets[ControllerField.ANTI_WINDUP].setCurrentIndex(index)

        self._field_widgets[ControllerField.CONSTRAINT_MIN].setText(f"{self._vm_controller.constraint_min}")
        self._field_widgets[ControllerField.CONSTRAINT_MAX].setText(f"{self._vm_controller.constraint_max}")

