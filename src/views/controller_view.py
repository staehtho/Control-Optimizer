from __future__ import annotations
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QDoubleValidator, QValidator
from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QLineEdit, QHBoxLayout, QGraphicsOpacityEffect

from app_domain.controlsys import AntiWindup
from app_types import ControllerField, FieldConfig, SectionConfig, ConnectSignalConfig
from .view_mixin import ViewMixin
from views.widgets import AspectRatioSvgWidget
from resources.resources import Icons
from resources.blockdiagram import load_controller_diagram

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from viewmodels import ControllerViewModel
    from views.widgets import SectionFrame

# TODO: block diagram like the closed loop in pso, now it is to saml

class OptionalDoubleValidator(QDoubleValidator):
    def validate(self, input_text: str, pos: int):
        if input_text.strip() == "":
            return QValidator.State.Intermediate, input_text, pos
        return super().validate(input_text, pos)


FIELDS: list[FieldConfig | SectionConfig] = [
    SectionConfig(ControllerField.CONSTRAINT, [
        FieldConfig(ControllerField.CONSTRAINT_MAX, QLineEdit),
        FieldConfig(ControllerField.CONSTRAINT_MIN, QLineEdit),
    ]),

    SectionConfig(ControllerField.ANTI_WINDUP, [
        FieldConfig(ControllerField.ANTI_WINDUP_METHODE, QComboBox),
        FieldConfig(ControllerField.FACTOR_KA, QLineEdit),
    ]),

    SectionConfig(ControllerField.FILTER_TIME_CONSTANT, [
        FieldConfig(ControllerField.TUNING_FACTOR, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6)),
        FieldConfig(ControllerField.SAMPLING_RATE, QLineEdit, validator=OptionalDoubleValidator(0.0, 1e9, 6)),
    ]),

    SectionConfig(ControllerField.CONTROLLER_TYPE, [
        FieldConfig(ControllerField.TYPE, QLabel),
    ])
]


class ControllerView(ViewMixin, QWidget):
    """View for configuring controller parameters and anti-windup settings."""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, ui_context: UiContext, vm_controller: ControllerViewModel, parent: QWidget = None):
        QWidget.__init__(self, parent)

        self._vm_controller = vm_controller

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.controller, self._title_icon_size)
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

        self._frm_controller = self._create_controller_frame()
        main_layout.addWidget(self._frm_controller)
        main_layout.addStretch()
        main_layout.addLayout(self._create_navigation_buttons_layout(parent=self))

        self.setLayout(main_layout)

    def _create_controller_frame(self) -> SectionFrame:
        """Create the controller configuration card."""
        frame: SectionFrame
        frame, frame_layout = self._create_card(parent=self)

        frame_layout.addLayout(self._create_grid(FIELDS))

        svg_widget = AspectRatioSvgWidget()
        svg_widget.set_initial_scale(2)
        frame_layout.addWidget(svg_widget)
        self.field_widgets.setdefault(ControllerField.BLOCK_DIAGRAM, svg_widget)
        self._load_block_diagram()

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._connect_object_signals(self._get_widget_bindings())

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_controller.validationFailed.connect(self._on_validation_failed)
        self._vm_controller.kaEnabledChanged.connect(self._on_ka_enable_changed)

        self._connect_object_signals(self._get_vm_bindings())

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        super()._retranslate()

        self._lbl_title.setText(self.tr("Controller"))
        self._frm_controller.setText(self.tr("Parameters"))

        labels = {
            ControllerField.ANTI_WINDUP: self.tr("Anti Windup"),
            ControllerField.ANTI_WINDUP_METHODE: self.tr("Methode"),
            ControllerField.CONSTRAINT: self.tr("Constraint"),
            ControllerField.CONSTRAINT_MIN: self.tr("Minimum"),
            ControllerField.CONSTRAINT_MAX: self.tr("Maximum"),
            ControllerField.FACTOR_KA: self.tr("Ka"),
            ControllerField.FILTER_TIME_CONSTANT: self.tr("Filter Time Constant Tf"),
            ControllerField.TUNING_FACTOR: self.tr("N"),
            ControllerField.SAMPLING_RATE: self.tr("Sampling Rate [Hz]"),
            ControllerField.CONTROLLER_TYPE: self.tr("Controller Type"),
            ControllerField.TYPE: self.tr("Type"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        # place holder
        txt: QLineEdit = self.field_widgets.get(ControllerField.SAMPLING_RATE)
        txt.setPlaceholderText(self.tr("Sampling rate unknown"))

        enums = {ControllerField.ANTI_WINDUP_METHODE: AntiWindup}
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self.field_widgets[key], data)

        self._apply_tool_tips()

    def _apply_tool_tips(self) -> None:

        tool_tips: dict[ControllerField, Any] = {
            ControllerField.TUNING_FACTOR: self.tr(
                """Defines the filter factor N used to compute the filter time constant Tf = Td/N.
                Smaller values of N result in stronger filtering and a smoother but slower control response."""
            ),
            ControllerField.SAMPLING_RATE: self.tr(
                """The filter time constant Tf is automatically limited by the system’s sampling rate and
                the simulation time step to ensure stable and proper behavior.
                If the sampling rate is unknown, leave this field empty to receive a recommended value."""
            )
        }

        for key, tool_tip in tool_tips.items():
            field = self.field_widgets[key]
            field.setToolTip(tool_tip)

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            ControllerField.TYPE: self._vm_controller.controller_type,
            ControllerField.FACTOR_KA: self._vm_controller.ka,
            ControllerField.CONSTRAINT_MIN: self._vm_controller.constraint_min,
            ControllerField.CONSTRAINT_MAX: self._vm_controller.constraint_max,
            ControllerField.TUNING_FACTOR: self._vm_controller.tuning_factor,
            ControllerField.SAMPLING_RATE:
                self._vm_controller.sampling_rate if self._vm_controller.sampling_rate is not None else "",
        }
        for key, value in init_value.items():
            self.field_widgets[key].setText(f"{value}")

        index = self.field_widgets[ControllerField.ANTI_WINDUP_METHODE].findData(self._vm_controller.anti_windup)
        if index >= 0:
            self.field_widgets[ControllerField.ANTI_WINDUP_METHODE].setCurrentIndex(index)

        self._on_ka_enable_changed()

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        self._load_block_diagram()

        icon = self._load_icon(Icons.controller, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_ka_enable_changed(self) -> None:
        lbl: QLabel = self.labels.get(ControllerField.FACTOR_KA)
        widget: QLineEdit = self.field_widgets.get(ControllerField.FACTOR_KA)

        visible = self._vm_controller.ka_enabled

        for w in (lbl, widget):
            w.setVisible(True)  # keep in layout
            w.setEnabled(visible)
            effect = w.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(w)
                w.setGraphicsEffect(effect)
            effect.setOpacity(1.0 if visible else 0.0)

    # ============================================================
    # Internal helpers
    # ============================================================
    def _load_block_diagram(self) -> None:
        """Build and recolor the controller block diagram SVG."""
        merged_svg = load_controller_diagram(
            self._vm_controller.anti_windup,
            (self._vm_controller.constraint_min, self._vm_controller.constraint_max),
            self._vm_theme.get_svg_color_map(),
        )

        self.field_widgets.get(ControllerField.BLOCK_DIAGRAM).set_svg_bytes(merged_svg.encode("utf-8"))

    def _get_widget_bindings(self) -> list[ConnectSignalConfig]:
        k_constraint_min = ControllerField.CONSTRAINT_MIN
        k_constraint_max = ControllerField.CONSTRAINT_MAX
        k_anti_windup_methode = ControllerField.ANTI_WINDUP_METHODE
        k_factor_ka = ControllerField.FACTOR_KA
        k_tuning_factor = ControllerField.TUNING_FACTOR
        k_sampling_rate = ControllerField.SAMPLING_RATE

        return [
            ConnectSignalConfig(
                key=k_constraint_min,
                signal_name="editingFinished",
                attr_name="_vm_controller.constraint_min",
                widget=self.field_widgets.get(k_constraint_min),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_constraint_max,
                signal_name="editingFinished",
                attr_name="_vm_controller.constraint_max",
                widget=self.field_widgets.get(k_constraint_max),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_anti_windup_methode,
                signal_name="currentIndexChanged",
                attr_name="_vm_controller.anti_windup",
                widget=self.field_widgets.get(k_anti_windup_methode),
                kwargs={"value_type": AntiWindup},
                main_event_handler=self._on_widget_changed,
                post_event_handler=self._load_block_diagram
            ),
            ConnectSignalConfig(
                key=k_factor_ka,
                signal_name="editingFinished",
                attr_name="_vm_controller.ka",
                widget=self.field_widgets.get(k_factor_ka),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_tuning_factor,
                signal_name="editingFinished",
                attr_name="_vm_controller.tuning_factor",
                widget=self.field_widgets.get(k_tuning_factor),
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_sampling_rate,
                signal_name="textEdited",
                attr_name="_vm_controller.sampling_rate",
                widget=self.field_widgets.get(k_sampling_rate),
                kwargs={"commit": False, "get_text": lambda: self.field_widgets.get(k_sampling_rate).text()},
                override_event_handler=self._vm_controller.set_sampling_rate_text,
            ),
            ConnectSignalConfig(
                key=k_sampling_rate,
                signal_name="editingFinished",
                attr_name="_vm_controller.sampling_rate",
                widget=self.field_widgets.get(k_sampling_rate),
                kwargs={"commit": True, "get_text": lambda: self.field_widgets.get(k_sampling_rate).text()},
                override_event_handler=self._vm_controller.set_sampling_rate_text,
            ),
        ]

    def _get_vm_bindings(self) -> list[ConnectSignalConfig]:
        k_constraint_min = ControllerField.CONSTRAINT_MIN
        k_constraint_max = ControllerField.CONSTRAINT_MAX
        k_anti_windup_methode = ControllerField.ANTI_WINDUP_METHODE
        k_factor_ka = ControllerField.FACTOR_KA
        k_tuning_factor = ControllerField.TUNING_FACTOR
        k_sampling_rate = ControllerField.SAMPLING_RATE

        return [
            ConnectSignalConfig(
                key=k_constraint_min,
                signal_name="constraintMinChanged",
                attr_name="constraint_min",
                widget=self._vm_controller,
                kwargs={"field": self.field_widgets.get(k_constraint_min)},
                main_event_handler=self._on_vm_changed,
                post_event_handler=self._load_block_diagram,
            ),
            ConnectSignalConfig(
                key=k_constraint_max,
                signal_name="constraintMaxChanged",
                attr_name="constraint_max",
                widget=self._vm_controller,
                kwargs={"field": self.field_widgets.get(k_constraint_max)},
                main_event_handler=self._on_vm_changed,
                post_event_handler=self._load_block_diagram,
            ),
            ConnectSignalConfig(
                key=k_anti_windup_methode,
                signal_name="antiWindupChanged",
                attr_name="anti_windup",
                widget=self._vm_controller,
                kwargs={"field": self.field_widgets.get(k_anti_windup_methode)},
                main_event_handler=self._on_vm_changed
            ),
            ConnectSignalConfig(
                key=k_factor_ka,
                signal_name="kaChanged",
                attr_name="ka",
                widget=self._vm_controller,
                kwargs={"field": self.field_widgets.get(k_factor_ka)},
                main_event_handler=self._on_vm_changed
            ),
            ConnectSignalConfig(
                key=k_tuning_factor,
                signal_name="tuningFactorChanged",
                attr_name="tuning_factor",
                widget=self._vm_controller,
                kwargs={"field": self.field_widgets.get(k_tuning_factor)},
                main_event_handler=self._on_vm_changed
            ),
            ConnectSignalConfig(
                key=k_sampling_rate,
                signal_name="samplingRateChanged",
                attr_name="sampling_rate",
                widget=self._vm_controller,
                kwargs={"field": self.field_widgets.get(k_sampling_rate)},
                main_event_handler=self._on_vm_changed
            ),
        ]
