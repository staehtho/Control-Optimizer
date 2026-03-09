from functools import partial

from PySide6.QtWidgets import QWidget, QComboBox, QLineEdit, QFrame, QLabel, QGridLayout
from PySide6.QtGui import QIntValidator, Qt

from app_domain import UiContext
from app_domain.controlsys import MySolver
from viewmodels.types import SettingsField, LanguageType, ThemeType
from .base_view import BaseView, FieldConfig, SectionConfig

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
            FieldConfig(SettingsField.PSO_ITERATIONS, QLineEdit, validator=QIntValidator),
            FieldConfig(SettingsField.PSO_PARTICLES, QLineEdit, validator=QIntValidator),
        ]),
    ],
}


class SettingsView(BaseView, QWidget):
    def __init__(self, ui_context: UiContext, parent: QWidget = None):
        QWidget.__init__(self, parent)

        self._vm_theme = ui_context.vm_theme
        self._vm_settings = ui_context.settings

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title
        self._lbl_title = QLabel(self)
        self._lbl_title.setObjectName("viewTitle")
        main_layout.addWidget(self._lbl_title, 0)

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
        frame = QFrame(self)
        layout = self._create_grid(FIELDS.get(key), 2)

        frame.setLayout(layout)
        return frame

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        attributes: dict[SettingsField, tuple[str, str, object]] = {
            SettingsField.SOLVER_TYPE: ("currentIndexChanged", "_vm_settings.solver", MySolver),
            SettingsField.PSO_ITERATIONS: ("editingFinished", "_vm_settings.pso_iterations", int),
            SettingsField.PSO_PARTICLES: ("editingFinished", "_vm_settings.pso_particle", int),
        }
        for key, value in attributes.items():
            attr, vm_attr, value_type = value
            getattr(self._field_widgets[key], attr).connect(
                partial(self._on_widget_changed, key, vm_attr, value_type=value_type))

        self._field_widgets.get(SettingsField.LANGUAGE).currentIndexChanged.connect(
            self._on_language_index_changed
        )
        self._field_widgets.get(SettingsField.THEME).currentIndexChanged.connect(
            self._on_theme_index_changed
        )

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        ...

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
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
            self._labels[key].setText(labels[key])

        item_enums = {
            SettingsField.LANGUAGE: self._enum_translation(LanguageType),
            SettingsField.THEME: self._enum_translation(ThemeType),
            SettingsField.SOLVER_TYPE: self._enum_translation(MySolver)
        }

        for key in item_enums:
            self._cmb_add_item(self._field_widgets[key], item_enums[key])

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            SettingsField.SOLVER_TIME_STEP: self._vm_settings.time_stamp,
            SettingsField.PSO_ITERATIONS: self._vm_settings.pso_iterations,
            SettingsField.PSO_PARTICLES: self._vm_settings.pso_particle,
        }
        for key, value in init_value.items():
            self._field_widgets[key].setText(f"{value}")

        attributes: dict[SettingsField, tuple[str, str]] = {
            SettingsField.LANGUAGE: ("_vm_lang", "current_language"),
            SettingsField.THEME: ("_vm_theme", "current_theme"),
            SettingsField.SOLVER_TYPE: ("_vm_settings", "solver")
        }
        for key, item in attributes.items():
            index = self._field_widgets[key].findData(getattr(getattr(self, item[0]), item[1]))
            if index >= 0:
                self._field_widgets[key].setCurrentIndex(index)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_language_index_changed(self, index: int) -> None:
        widget = self._field_widgets.get(SettingsField.LANGUAGE)
        value = widget.itemData(index)
        self._vm_lang.set_language(LanguageType(value))

    def _on_theme_index_changed(self, index: int) -> None:
        widget = self._field_widgets.get(SettingsField.THEME)
        value = widget.itemData(index)
        self._vm_theme.set_theme(ThemeType(value))
