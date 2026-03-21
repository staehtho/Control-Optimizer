from functools import partial
from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QLineEdit, QHBoxLayout

from app_domain.ui_context import UiContext
from app_domain.controlsys import AntiWindup
from utils import recolor_svg, merge_svgs, SvgLayer
from viewmodels import ControllerViewModel
from app_types import ControllerField, FieldConfig, SectionConfig
from .view_mixin import ViewMixin
from views.widgets import SectionFrame, AspectRatioSvgWidget
from views.resources import BLOCK_DIAGRAM_DIR, BlockDiagram, Icons

FIELDS: list[FieldConfig] = [
    SectionConfig(ControllerField.CONSTRAINT, [
        FieldConfig(ControllerField.CONSTRAINT_MIN, QLineEdit),
        FieldConfig(ControllerField.CONSTRAINT_MAX, QLineEdit),
    ]),

    FieldConfig(ControllerField.CONTROLLER_TYPE, QLabel),
    FieldConfig(ControllerField.ANTI_WINDUP, QComboBox),
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
        icon = self._load_icon(Icons.controller, self._titel_icon_size)
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

        self._frm_controller = self._create_controller_frame()
        main_layout.addWidget(self._frm_controller)
        main_layout.addStretch()

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
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            widget = self.field_widgets[key]
            getattr(widget, attr).connect(partial(self._on_widget_changed, widget, key, vm_attr, value_type=value_type))

        self.field_widgets.get(ControllerField.ANTI_WINDUP).currentIndexChanged.connect(
            self._on_index_changed_anti_windup)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_controller.validationFailed.connect(self._on_validation_failed)
        self._vm_controller.constraintMinChanged.connect(self._on_vm_constraint_min_changed)
        self._vm_controller.constraintMaxChanged.connect(self._on_vm_constraint_max_changed)
        self._vm_controller.antiWindupChanged.connect(
            partial(self._on_vm_changed, ControllerField.ANTI_WINDUP, "_vm_controller.anti_windup")
        )

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Controller"))
        self._frm_controller.setText(self.tr("Parameters"))

        labels = {
            ControllerField.CONTROLLER_TYPE: self.tr("Controller Type"),
            ControllerField.ANTI_WINDUP: self.tr("Anti Windup"),
            ControllerField.CONSTRAINT: self.tr("Constraint"),
            ControllerField.CONSTRAINT_MIN: self.tr("Minimum"),
            ControllerField.CONSTRAINT_MAX: self.tr("Maximum"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        enums = {ControllerField.ANTI_WINDUP: AntiWindup}
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self.field_widgets[key], data)

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self.field_widgets[ControllerField.CONTROLLER_TYPE].setText(self._vm_controller.controller_type)

        index = self.field_widgets[ControllerField.ANTI_WINDUP].findData(self._vm_controller.anti_windup)
        if index >= 0:
            self.field_widgets[ControllerField.ANTI_WINDUP].setCurrentIndex(index)

        self.field_widgets[ControllerField.CONSTRAINT_MIN].setText(f"{self._vm_controller.constraint_min}")
        self.field_widgets[ControllerField.CONSTRAINT_MAX].setText(f"{self._vm_controller.constraint_max}")

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        self._load_block_diagram()

        icon = self._load_icon(Icons.controller, self._titel_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._titel_icon_size, self._titel_icon_size))

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
        widget = self.field_widgets.get(ControllerField.ANTI_WINDUP)
        value = widget.itemData(index)
        self._vm_controller.anti_windup = value
        self._load_block_diagram()

    # ============================================================
    # Internal helpers
    # ============================================================
    def _load_block_diagram(self) -> None:
        """Build and recolor the controller block diagram SVG."""
        y = 125
        node_x = 150
        sum_x = 475
        svgs = [
            (BlockDiagram.blank_base, (0, 0)),
            (BlockDiagram.controller_in, (0, y)),
            (BlockDiagram.controller_out, (sum_x, y)),
            (BlockDiagram.p_path, (node_x, y)),
            (BlockDiagram.d_path, (node_x, y))
        ]

        match self._vm_controller.anti_windup:
            case AntiWindup.BACKCALCULATION:
                svgs.append((BlockDiagram.backcalculation, (node_x, y)))
            case AntiWindup.CLAMPING:
                svgs.append((BlockDiagram.clamping, (node_x, y)))
            case AntiWindup.CONDITIONAL:
                svgs.append((BlockDiagram.conditional, (node_x, y)))
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

        # set min and max constraint
        merged_svg = merged_svg.replace("min: ###", f"min: {self._vm_controller.constraint_min}")
        merged_svg = merged_svg.replace("max: ###", f"max: {self._vm_controller.constraint_max}")

        recolored = recolor_svg(merged_svg, self._vm_theme.get_svg_color_map())
        self.field_widgets.get(ControllerField.BLOCK_DIAGRAM).set_svg_bytes(recolored.encode("utf-8"))
