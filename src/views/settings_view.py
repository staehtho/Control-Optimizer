from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtWidgets import QWidget, QComboBox, QLineEdit, QFrame, QLabel, QGridLayout, QHBoxLayout
from PySide6.QtGui import QIntValidator

from app_domain.controlsys import MySolver
from app_types import SettingsField, LanguageType, ThemeType, FieldConfig, SectionConfig, ConnectSignalConfig
from views.view_mixin import ViewMixin
from resources.resources import Icons

if TYPE_CHECKING:
    from app_domain import UiContext


FIELDS: dict[str, list[FieldConfig | SectionConfig]] = {
    "language": [
        SectionConfig(SettingsField.LANGUAGE, [
            FieldConfig(SettingsField.LANGUAGE, QComboBox, create_label=False),
        ]),
    ],
    "theme": [
        SectionConfig(SettingsField.THEME, [
            FieldConfig(SettingsField.THEME, QComboBox, create_label=False),
        ]),
    ],
    "solver": [
        SectionConfig(SettingsField.SOLVER, [
            FieldConfig(SettingsField.SOLVER_TYPE, QComboBox),
            FieldConfig(SettingsField.SOLVER_TIME_STEP, QLineEdit),
        ]),
    ],
    "pso": [
        SectionConfig(SettingsField.PSO, [
            FieldConfig(SettingsField.PSO_ITERATIONS, QLineEdit, validator=QIntValidator()),
            FieldConfig(SettingsField.PSO_PARTICLES, QLineEdit, validator=QIntValidator()),
        ]),
    ],
}


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
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(3, 1)

        count = 0
        for key in FIELDS.keys():
            frame = self._create_frame(key)
            grid_layout.addWidget(frame, count, 1)
            count += 1

        grid_layout.setRowStretch(count, 1)

        main_layout.addLayout(grid_layout, 1)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_frame(self, key: str) -> QFrame:
        """Create a settings section frame for the given key."""
        frame = QFrame(self)
        layout = self._create_grid(FIELDS[key], 1)

        frame.setLayout(layout)
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
        self._connect_object_signals(self._get_vm_bindings())

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Settings"))

        labels = {
            SettingsField.LANGUAGE: self.tr("Language"),
            SettingsField.THEME: self.tr("Theme"),
            SettingsField.SOLVER: self.tr("Solver"),
            SettingsField.SOLVER_TYPE: self.tr("Type"),
            SettingsField.SOLVER_TIME_STEP: self.tr("Time Step"),
            SettingsField.PSO: self.tr("PSO"),
            SettingsField.PSO_ITERATIONS: self.tr("Iterations"),
            SettingsField.PSO_PARTICLES: self.tr("Particles"),
        }

        for key in labels.keys():
            self.labels[key].setText(labels[key])

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
            SettingsField.PSO_ITERATIONS: self._vm_settings.pso_iterations,
            SettingsField.PSO_PARTICLES: self._vm_settings.pso_particle,
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
        k_time_step = SettingsField.SOLVER_TIME_STEP
        k_pos_iterations = SettingsField.PSO_ITERATIONS
        k_pso_particles = SettingsField.PSO_PARTICLES

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
            ConnectSignalConfig(
                key=k_time_step,
                signal_name="editingFinished",
                attr_name="_vm_settings.time_step",
                widget=self.field_widgets[k_time_step],
                kwargs={"value_type": float},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_pos_iterations,
                signal_name="editingFinished",
                attr_name="_vm_settings.pso_iterations",
                widget=self.field_widgets[k_pos_iterations],
                kwargs={"value_type": int},
                main_event_handler=self._on_widget_changed
            ),
            ConnectSignalConfig(
                key=k_pso_particles,
                signal_name="editingFinished",
                attr_name="_vm_settings.pso_particle",
                widget=self.field_widgets[k_pso_particles],
                kwargs={"value_type": int},
                main_event_handler=self._on_widget_changed
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
                SettingsField.PSO_ITERATIONS,
                "psoIterationsChanged",
                "pso_iterations"
            ),
            _wrapper(
                SettingsField.PSO_PARTICLES,
                "psoParticleChanged",
                "pso_particle"
            ),
        ]
