from __future__ import annotations
from typing import TYPE_CHECKING
from functools import partial

from PySide6.QtGui import QDoubleValidator, QValidator
from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QLineEdit, QHBoxLayout, QGraphicsOpacityEffect

from app_domain.controlsys import AntiWindup
from app_types import ControllerField, FieldConfig, SectionConfig
from .view_mixin import ViewMixin
from views.widgets import AspectRatioSvgWidget
from resources.resources import Icons
from resources.blockdiagram import load_controller_diagram

if TYPE_CHECKING:
    from app_domain.ui_context import UiContext
    from viewmodels import ControllerViewModel
    from views.widgets import SectionFrame


class OptionalDoubleValidator(QDoubleValidator):
    def validate(self, input_text: str, pos: int):
        if input_text.strip() == "":
            return QValidator.State.Intermediate, input_text, pos
        return super().validate(input_text, pos)


FIELDS: list[FieldConfig | SectionConfig] = [
    SectionConfig(ControllerField.CONSTRAINT, [
        FieldConfig(ControllerField.CONSTRAINT_MIN, QLineEdit),
        FieldConfig(ControllerField.CONSTRAINT_MAX, QLineEdit),
    ]),

    SectionConfig(ControllerField.ANTI_WINDUP, [
        FieldConfig(ControllerField.ANTI_WINDUP_METHODE, QComboBox),
        FieldConfig(ControllerField.FACTOR_KA, QLineEdit),
    ]),

    SectionConfig(ControllerField.FILTER_TIME_CONSTANT, [
        FieldConfig(ControllerField.TUNING_FACTOR, QLineEdit, validator=QDoubleValidator(0.0, 1e9, 6)),
        FieldConfig(ControllerField.SAMPLING_RATE, QLineEdit, validator=OptionalDoubleValidator(0.0, 1e9, 6)),
    ]),

    FieldConfig(ControllerField.CONTROLLER_TYPE, QLabel),
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
        attributes: dict[ControllerField, tuple[str, str, object]] = {
            ControllerField.CONSTRAINT_MIN: ("editingFinished", "_vm_controller.constraint_min", float),
            ControllerField.CONSTRAINT_MAX: ("editingFinished", "_vm_controller.constraint_max", float),
            ControllerField.FACTOR_KA: ("editingFinished", "_vm_controller.ka", float),
            ControllerField.TUNING_FACTOR: ("editingFinished", "_vm_controller.tuning_factor", float),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            widget = self.field_widgets[key]
            getattr(widget, attr).connect(partial(self._on_widget_changed, widget, key, vm_attr, value_type=value_type))

        sampling_rate_widget: QLineEdit = self.field_widgets.get(ControllerField.SAMPLING_RATE)
        if sampling_rate_widget is not None:
            sampling_rate_widget.textEdited.connect(
                partial(self._vm_controller.set_sampling_rate_text, commit=False)
            )
            sampling_rate_widget.editingFinished.connect(self._on_sampling_rate_editing_finished)

        self.field_widgets.get(ControllerField.ANTI_WINDUP_METHODE).currentIndexChanged.connect(
            self._on_index_changed_anti_windup)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_controller.validationFailed.connect(self._on_validation_failed)
        self._vm_controller.constraintMinChanged.connect(self._on_vm_constraint_min_changed)
        self._vm_controller.constraintMaxChanged.connect(self._on_vm_constraint_max_changed)

        attributes: dict[ControllerField, tuple[str, str]] = {
            ControllerField.ANTI_WINDUP_METHODE: ("antiWindupChanged", "_vm_controller.anti_windup"),
            ControllerField.FACTOR_KA: ("kaChanged", "_vm_controller.ka"),
            ControllerField.TUNING_FACTOR: ("tuningFactorChanged", "_vm_controller.tuning_factor"),
            ControllerField.SAMPLING_RATE: ("samplingRateChanged", "_vm_controller.sampling_rate"),
        }

        for key, value in attributes.items():
            signal, vm_attr = value
            vm = self._vm_controller
            getattr(vm, signal).connect(partial(self._on_vm_changed, key, vm_attr))

        self._vm_controller.kaEnabledChanged.connect(self._on_ka_enable_changed)

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        super()._retranslate()

        self._lbl_title.setText(self.tr("Controller"))
        self._frm_controller.setText(self.tr("Parameters"))

        labels = {
            ControllerField.CONTROLLER_TYPE: self.tr("Controller Type"),
            ControllerField.ANTI_WINDUP: self.tr("Anti Windup"),
            ControllerField.ANTI_WINDUP_METHODE: self.tr("Methode"),
            ControllerField.CONSTRAINT: self.tr("Constraint"),
            ControllerField.CONSTRAINT_MIN: self.tr("Minimum"),
            ControllerField.CONSTRAINT_MAX: self.tr("Maximum"),
            ControllerField.FACTOR_KA: self.tr("Ka"),
            ControllerField.FILTER_TIME_CONSTANT: self.tr("Filter Time Constant Tf"),
            ControllerField.TUNING_FACTOR: self.tr("N"),
            ControllerField.SAMPLING_RATE: self.tr("Sampling Rate [Hz]"),
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

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            ControllerField.CONTROLLER_TYPE: self._vm_controller.controller_type,
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
    # ViewModel change handlers
    # ============================================================
    def _on_vm_constraint_min_changed(self) -> None:
        """Handle VM constraint minimum changed."""
        self._on_vm_changed(ControllerField.CONSTRAINT_MIN, "_vm_controller.constraint_min")
        self._load_block_diagram()

    def _on_vm_constraint_max_changed(self) -> None:
        """Handle VM constraint maximum changed."""
        self._on_vm_changed(ControllerField.CONSTRAINT_MAX, "_vm_controller.constraint_max")
        self._load_block_diagram()

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_index_changed_anti_windup(self, index: int) -> None:
        """Handle anti-windup selection changes."""
        widget = self.field_widgets.get(ControllerField.ANTI_WINDUP_METHODE)
        value = widget.itemData(index)
        self._vm_controller.anti_windup = value
        self._load_block_diagram()

    def _on_ka_enable_changed(self) -> None:
        lbl: QLabel = self.labels.get(ControllerField.FACTOR_KA)
        widget: QLineEdit = self.field_widgets.get(ControllerField.FACTOR_KA)

        visible = self._vm_controller.ka_enabled

        for w in (lbl, widget):
            w.setVisible(True)  # keep in layout
            w.setEnabled(visible)
            eff = w.graphicsEffect()
            if eff is None:
                eff = QGraphicsOpacityEffect(w)
                w.setGraphicsEffect(eff)
            eff.setOpacity(1.0 if visible else 0.0)

    def _on_sampling_rate_editing_finished(self) -> None:
        if self.initializing:
            return

        widget: QLineEdit = self.field_widgets.get(ControllerField.SAMPLING_RATE)
        if widget is None:
            return

        self._vm_controller.set_sampling_rate_text(widget.text(), commit=True)

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
