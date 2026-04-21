from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtWidgets import QWidget, QComboBox, QLineEdit, QFrame, QLabel, QGridLayout, QHBoxLayout, QPushButton, \
    QSizePolicy
from PySide6.QtGui import QIntValidator, QDoubleValidator

from app_domain.controlsys import MySolver
from app_types import SettingsField, LanguageType, ThemeType, FieldConfig, SectionConfig, ConnectSignalConfig, NavLabels
from views.view_mixin import ViewMixin
from resources.resources import Icons

if TYPE_CHECKING:
    from app_domain import UiContext

FIELDS_RIGHT: list[FieldConfig | SectionConfig] = [
    SectionConfig(SettingsField.LANGUAGE, [
        FieldConfig(SettingsField.LANGUAGE, QComboBox, create_label=False),
    ]),
    SectionConfig(SettingsField.THEME, [
        FieldConfig(SettingsField.THEME, QComboBox, create_label=False),
    ]),
    SectionConfig(SettingsField.SOLVER, [
        FieldConfig(SettingsField.SOLVER_TYPE, QComboBox),
        FieldConfig(SettingsField.SOLVER_TIME_STEP, QLineEdit),
    ]),
]

FIELDS_LEFT: list[FieldConfig | SectionConfig] = [
    SectionConfig(SettingsField.PSO, [
        FieldConfig(
            SettingsField.PSO_REPEAT_RUNS,
            QLineEdit,
            validator=QIntValidator(1, 1000),
        ),
        FieldConfig(
            SettingsField.PSO_SWARM_SIZE,
            QLineEdit,
            validator=QIntValidator(1, 10000),
        ),
        FieldConfig(
            SettingsField.PSO_RANDOMNESS,
            QLineEdit,
            validator=QDoubleValidator(0.0, 10.0, 6),
        ),
        FieldConfig(
            SettingsField.PSO_U1,
            QLineEdit,
            validator=QDoubleValidator(0.0, 4.0, 6),
        ),
        FieldConfig(
            SettingsField.PSO_U2,
            QLineEdit,
            validator=QDoubleValidator(0.0, 4.0, 6),
        ),
        FieldConfig(
            SettingsField.PSO_INITIAL_RANGE_START,
            QLineEdit,
            validator=QDoubleValidator(-1e6, 1e6, 6),
        ),
        FieldConfig(
            SettingsField.PSO_INITIAL_RANGE_END,
            QLineEdit,
            validator=QDoubleValidator(-1e6, 1e6, 6),
        ),
        FieldConfig(
            SettingsField.PSO_INITIAL_SWARM_SPAN,
            QLineEdit,
            validator=QIntValidator(1, 1_000_000),
        ),
        FieldConfig(
            SettingsField.PSO_MIN_NEIGHBORS_FRACTION,
            QLineEdit,
            validator=QDoubleValidator(0.0, 1.0, 6),
        ),
        FieldConfig(
            SettingsField.PSO_MAX_STALL,
            QLineEdit,
            validator=QIntValidator(1, 10_000),
        ),
        FieldConfig(
            SettingsField.PSO_MAX_ITER,
            QLineEdit,
            validator=QIntValidator(1, 1_000_000),
        ),
        FieldConfig(
            SettingsField.PSO_STALL_WINDOWS_REQUIRED,
            QLineEdit,
            validator=QIntValidator(1, 100),
        ),
        FieldConfig(
            SettingsField.PSO_SPACE_FACTOR,
            QLineEdit,
            validator=QDoubleValidator(0.0, 1.0, 8),
        ),
        FieldConfig(
            SettingsField.PSO_CONVERGENCE_FACTOR,
            QLineEdit,
            validator=QDoubleValidator(0.0, 1.0, 8),
        ),
        FieldConfig(SettingsField.PSO_RESET_SETTINGS, QPushButton)
    ]),
]


class SettingsView(ViewMixin, QWidget):
    """View for editing application settings (language, theme, solver, PSO)."""

    # ============================================================
    # Initialization
    # ============================================================

    def __init__(self, ui_context: UiContext, parent: QWidget = None):
        QWidget.__init__(self, parent)

        self._vm_settings = ui_context.settings

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.settings, self._title_icon_size)
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

        grid_layout = QGridLayout()
        grid_layout.addLayout(self._create_grid(FIELDS_LEFT, 2), 0, 0, 4, 1)
        grid_layout.addLayout(self._create_grid(FIELDS_RIGHT, 2), 0, 1)

        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        main_layout.addLayout(grid_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._connect_object_signals(self._get_widget_bindings())

        self.field_widgets[SettingsField.PSO_RESET_SETTINGS].clicked.connect(
            self._vm_settings.reset_to_defaults
        )

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._connect_object_signals(self._get_vm_bindings())

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self._enum_translation(NavLabels.SETTINGS))

        labels = {
            SettingsField.LANGUAGE: self.tr("Language"),
            SettingsField.THEME: self.tr("Theme"),
            SettingsField.SOLVER: self.tr("Solver"),
            SettingsField.SOLVER_TYPE: self.tr("Type"),
            SettingsField.SOLVER_TIME_STEP: self.tr("Time Step"),

            SettingsField.PSO: self.tr("Particle Swarm Optimization"),
            SettingsField.PSO_REPEAT_RUNS: self.tr("Repeat Runs"),
            SettingsField.PSO_SWARM_SIZE: self.tr("Number of Particles"),
            SettingsField.PSO_RANDOMNESS: self.tr("Randomness Factor"),
            SettingsField.PSO_U1: self.tr("Cognitive Factor (u1)"),
            SettingsField.PSO_U2: self.tr("Social Factor (u2)"),
            SettingsField.PSO_INITIAL_RANGE_START: self.tr("Initial Range (Min)"),
            SettingsField.PSO_INITIAL_RANGE_END: self.tr("Initial Range (Max)"),
            SettingsField.PSO_INITIAL_SWARM_SPAN: self.tr("Initial Swarm Span"),
            SettingsField.PSO_MIN_NEIGHBORS_FRACTION: self.tr("Min. Neighbors Fraction"),
            SettingsField.PSO_MAX_STALL: self.tr("Max Stall"),
            SettingsField.PSO_MAX_ITER: self.tr("Max Iterations"),
            SettingsField.PSO_STALL_WINDOWS_REQUIRED: self.tr("Required Stall Windows"),
            SettingsField.PSO_SPACE_FACTOR: self.tr("Search Space Factor"),
            SettingsField.PSO_CONVERGENCE_FACTOR: self.tr("Convergence Factor"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

        self.field_widgets[SettingsField.PSO_RESET_SETTINGS].setText(self.tr("Reset PSO Settings"))

        enums = {
            SettingsField.LANGUAGE: LanguageType,
            SettingsField.THEME: ThemeType,
            SettingsField.SOLVER_TYPE: MySolver
        }
        for key, value in enums.items():
            data = {k: self._enum_translation(k) for k in value}
            self._cmb_add_item(self.field_widgets[key], data)

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            SettingsField.SOLVER_TIME_STEP: self._vm_settings.time_step,
            SettingsField.PSO_REPEAT_RUNS: self._vm_settings.pso_repeat_runs,
            SettingsField.PSO_SWARM_SIZE: self._vm_settings.pso_swarm_size,
            SettingsField.PSO_RANDOMNESS: self._vm_settings.pso_randomness,
            SettingsField.PSO_U1: self._vm_settings.pso_u1,
            SettingsField.PSO_U2: self._vm_settings.pso_u2,
            SettingsField.PSO_INITIAL_RANGE_START: self._vm_settings.pso_initial_range_start,
            SettingsField.PSO_INITIAL_RANGE_END: self._vm_settings.pso_initial_range_end,
            SettingsField.PSO_INITIAL_SWARM_SPAN: self._vm_settings.pso_initial_swarm_span,
            SettingsField.PSO_MIN_NEIGHBORS_FRACTION: self._vm_settings.pso_min_neighbors_fraction,
            SettingsField.PSO_MAX_STALL: self._vm_settings.pso_max_stall,
            SettingsField.PSO_MAX_ITER: self._vm_settings.pso_max_iter,
            SettingsField.PSO_STALL_WINDOWS_REQUIRED: self._vm_settings.pso_stall_windows_required,
            SettingsField.PSO_SPACE_FACTOR: self._vm_settings.pso_space_factor,
            SettingsField.PSO_CONVERGENCE_FACTOR: self._vm_settings.pso_convergence_factor,
        }
        for key, value in init_value.items():
            self.field_widgets[key].setText(f"{value}")

        attributes: dict[SettingsField, tuple[str, str]] = {
            SettingsField.LANGUAGE: ("_vm_lang", "current_language"),
            SettingsField.THEME: ("_vm_theme", "current_theme"),
            SettingsField.SOLVER_TYPE: ("_vm_settings", "solver")
        }
        for key, item in attributes.items():
            index = self.field_widgets[key].findData(getattr(getattr(self, item[0]), item[1]))
            if index >= 0:
                self.field_widgets[key].setCurrentIndex(index)

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.settings, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))

    # ============================================================
    # UI event handlers
    # ============================================================
    @staticmethod
    def _on_index_changed(index: int, **kwargs: Any) -> None:
        """Handle index selection changes."""
        field = kwargs.get("field")
        if not isinstance(field, QComboBox) or field is None:
            raise TypeError(f"Expected QObject, got {type(field)}")

        setter = kwargs.get("setter")
        if not isinstance(setter, Callable) or setter is None:
            raise TypeError(f"Expected Callable, got {type(setter)}")

        setter(field.itemData(index))

    # ============================================================
    # Internal helpers
    # ============================================================
    def _get_widget_bindings(self) -> list[ConnectSignalConfig]:
        k_language = SettingsField.LANGUAGE
        k_theme = SettingsField.THEME
        k_solver_type = SettingsField.SOLVER_TYPE

        def _wrapper_editing_finished(key: SettingsField, attr: str, value_type: Any) -> ConnectSignalConfig:
            return ConnectSignalConfig(
                key=key,
                signal_name="editingFinished",
                attr_name=attr,
                widget=self.field_widgets[key],
                kwargs={"value_type": value_type},
                main_event_handler=self._on_widget_changed
            )

        return [
            ConnectSignalConfig(
                key=k_language,
                signal_name="currentIndexChanged",
                attr_name="",
                widget=self.field_widgets[k_language],
                kwargs={
                    "field": self.field_widgets[k_language],
                    "setter": lambda value: self._vm_lang.set_language(value)
                },
                override_event_handler=self._on_index_changed
            ),
            ConnectSignalConfig(
                key=k_theme,
                signal_name="currentIndexChanged",
                attr_name="",
                widget=self.field_widgets[k_theme],
                kwargs={
                    "field": self.field_widgets[k_theme],
                    "setter": lambda value: self._vm_theme.set_theme(value)
                },
                override_event_handler=self._on_index_changed
            ),
            ConnectSignalConfig(
                key=k_solver_type,
                signal_name="currentIndexChanged",
                attr_name="_vm_settings.solver",
                widget=self.field_widgets[k_solver_type],
                kwargs={"value_type": MySolver},
                main_event_handler=self._on_widget_changed
            ),
            _wrapper_editing_finished(
                SettingsField.SOLVER_TIME_STEP,
                "_vm_settings.time_step",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_REPEAT_RUNS,
                "_vm_settings.pso_repeat_runs",
                int
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_SWARM_SIZE,
                "_vm_settings.pso_swarm_size",
                int
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_RANDOMNESS,
                "_vm_settings.pso_randomness",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_U1,
                "_vm_settings.pso_u1",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_U2,
                "_vm_settings.pso_u2",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_INITIAL_RANGE_START,
                "_vm_settings.pso_initial_range_start",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_INITIAL_RANGE_END,
                "_vm_settings.pso_initial_range_end",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_INITIAL_SWARM_SPAN,
                "_vm_settings.pso_initial_swarm_span",
                int
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_MIN_NEIGHBORS_FRACTION,
                "_vm_settings.pso_min_neighbors_fraction",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_MAX_STALL,
                "_vm_settings.pso_max_stall",
                int
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_MAX_ITER,
                "_vm_settings.pso_max_iter",
                int
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_STALL_WINDOWS_REQUIRED,
                "_vm_settings.pso_stall_windows_required",
                int
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_SPACE_FACTOR,
                "_vm_settings.pso_space_factor",
                float
            ),
            _wrapper_editing_finished(
                SettingsField.PSO_CONVERGENCE_FACTOR,
                "_vm_settings.pso_convergence_factor",
                float
            ),
        ]

    def _get_vm_bindings(self) -> list[ConnectSignalConfig]:
        def _wrapper(key: SettingsField, signal_name: str, attr: str) -> ConnectSignalConfig:
            return ConnectSignalConfig(
                key=key,
                signal_name=signal_name,
                attr_name=attr,
                widget=self._vm_settings,
                kwargs={"field": self.field_widgets[key]},
                main_event_handler=self._on_vm_changed
            )

        return [
            _wrapper(
                SettingsField.SOLVER_TYPE,
                "solverChanged",
                "solver"
            ),
            _wrapper(
                SettingsField.SOLVER_TIME_STEP,
                "timeStepChanged",
                "time_step"
            ),
            _wrapper(
                SettingsField.PSO_REPEAT_RUNS,
                "psoRepeatRunsChanged",
                "pso_repeat_runs"
            ),
            _wrapper(
                SettingsField.PSO_SWARM_SIZE,
                "psoSwarmSizeChanged",
                "pso_swarm_size"
            ),
            _wrapper(
                SettingsField.PSO_RANDOMNESS,
                "psoRandomnessChanged",
                "pso_randomness"
            ),
            _wrapper(
                SettingsField.PSO_U1,
                "psoU1Changed",
                "pso_u1"
            ),
            _wrapper(
                SettingsField.PSO_U2,
                "psoU2Changed",
                "pso_u2"
            ),
            _wrapper(
                SettingsField.PSO_INITIAL_RANGE_START,
                "psoInitialRangeStartChanged",
                "pso_initial_range_start"
            ),
            _wrapper(
                SettingsField.PSO_INITIAL_RANGE_END,
                "psoInitialRangeEndChanged",
                "pso_initial_range_end"
            ),
            _wrapper(
                SettingsField.PSO_INITIAL_SWARM_SPAN,
                "psoInitialSwarmSpanChanged",
                "pso_initial_swarm_span"
            ),
            _wrapper(
                SettingsField.PSO_MIN_NEIGHBORS_FRACTION,
                "psoMinNeighborsFractionChanged",
                "pso_min_neighbors_fraction"
            ),
            _wrapper(
                SettingsField.PSO_MAX_STALL,
                "psoMaxStallChanged",
                "pso_max_stall"
            ),
            _wrapper(
                SettingsField.PSO_MAX_ITER,
                "psoMaxIterChanged",
                "pso_max_iter"
            ),
            _wrapper(
                SettingsField.PSO_STALL_WINDOWS_REQUIRED,
                "psoStallWindowsRequiredChanged",
                "pso_stall_windows_required"
            ),
            _wrapper(
                SettingsField.PSO_SPACE_FACTOR,
                "psoSpaceFactorChanged",
                "pso_space_factor"
            ),
            _wrapper(
                SettingsField.PSO_CONVERGENCE_FACTOR,
                "psoConvergenceFactorChanged",
                "pso_convergence_factor"
            ),
        ]
