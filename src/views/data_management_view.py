from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QCheckBox, QGraphicsOpacityEffect

from app_types import DataManagementField, FieldConfig, SectionConfig, ConnectSignalConfig, NavLabels
from resources.resources import Icons
from views.widgets.banner import InfoBanner, ErrorBanner
from views.widgets.path_widget import SavePathWidget, ImportPathWidget
from views.view_mixin import ViewMixin

if TYPE_CHECKING:
    from app_domain import UiContext
    from viewmodels import DataManagementViewModel
    from views.widgets import SectionFrame

FIELDS: list[FieldConfig | SectionConfig] = [
    SectionConfig(DataManagementField.REPORT, [
        FieldConfig(DataManagementField.REPORT_PLANT, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_EXCITATION_FUNCTION, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_CONTROLLER, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_PSO, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_BLOCK_DIAGRAM, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_TIME_DOMAIN, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_BODE, QCheckBox, create_label=False),
        FieldConfig(DataManagementField.REPORT_TRANSFER_FUNCTION, QCheckBox, create_label=False),
    ])
]

class DataManagementView(ViewMixin, QWidget):
    def __init__(
            self,
            ui_context: UiContext,
            vm_data: DataManagementViewModel,
            parent: QWidget = None
    ) -> None:
        QWidget.__init__(self, parent)

        self._vm_data = vm_data

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.data_management, self._title_icon_size)
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

        self._frm_export_import = self._create_export_import_frame()
        main_layout.addWidget(self._frm_export_import)

        self._frm_report = self._create_report_frame()
        main_layout.addWidget(self._frm_report)
        main_layout.addStretch()

        self._info_banner = InfoBanner("", self)
        self._error_banner = ErrorBanner("", self)

        main_layout.addWidget(self._info_banner)
        main_layout.addWidget(self._error_banner)

        self.setLayout(main_layout)

    def _create_export_import_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card()

        # export
        default_filename = f"control_optimizer_export_{datetime.now().strftime('%Y-%m-%d')}.json"
        file_filter = self.tr("JSON Files (*.json)")

        export_widget = SavePathWidget(default_filename, file_filter=file_filter, parent=self)
        layout.addWidget(export_widget)
        self.field_widgets.setdefault(DataManagementField.EXPORT, export_widget)

        # import
        import_widget = ImportPathWidget(file_filter=file_filter, parent=self)
        layout.addWidget(import_widget)
        self.field_widgets.setdefault(DataManagementField.IMPORT, import_widget)

        return frame

    def _create_report_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card()

        layout.addLayout(self._create_grid(FIELDS, 2))

        default_filename = f"control_optimizer_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        file_filter = self.tr("PDF Files (*.pdf)")

        save_report_widget = SavePathWidget(default_filename, file_filter=file_filter, parent=self)
        layout.addWidget(save_report_widget)
        self.field_widgets[DataManagementField.REPORT_DIALOG] = save_report_widget

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._connect_object_signals(self._get_widget_bindings())

        self.field_widgets[DataManagementField.EXPORT].exportRequested.connect(self._on_export_requested)
        self.field_widgets[DataManagementField.IMPORT].importRequested.connect(self._on_import_requested)
        self.field_widgets[DataManagementField.REPORT_DIALOG].exportRequested.connect(self._on_export_report_requested)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        self._vm_data.psoSimulationFinished.connect(self._on_pso_simulation_finished)
        self._vm_data.importFinished.connect(self._on_import_finished)
        self._vm_data.exportFinished.connect(self._on_export_finished)
        self._vm_data.reportFinished.connect(self._on_report_finished)
        self._vm_data.reportFailed.connect(self._on_report_failed)

        self._connect_object_signals(self._get_vm_bindings())

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self._enum_translation(NavLabels.DATA_MANAGEMENT))
        self._frm_export_import.setText(self.tr("Import and Export App Data"))
        self._frm_report.setText(self.tr("Create Report"))

        # retranslate PathWidget
        for key in (DataManagementField.EXPORT, DataManagementField.IMPORT, DataManagementField.REPORT_DIALOG):
            self.field_widgets[key].retranslate()

        self.labels[DataManagementField.REPORT].setText(self.tr("Report Configuration"))

        labels = {
            DataManagementField.REPORT_PLANT: self.tr("Plant Configuration"),
            DataManagementField.REPORT_EXCITATION_FUNCTION: self.tr("Excitation Function Configuration"),
            DataManagementField.REPORT_CONTROLLER: self.tr("Controller Configuration"),
            DataManagementField.REPORT_PSO: self.tr("PSO Configuration"),
            DataManagementField.REPORT_BLOCK_DIAGRAM: self.tr("Block Diagram"),
            DataManagementField.REPORT_TIME_DOMAIN: self.tr("Time Domain Plot"),
            DataManagementField.REPORT_BODE: self.tr("Bode Plot"),
            DataManagementField.REPORT_TRANSFER_FUNCTION: self.tr("Transfer Functions"),
        }

        for key in labels.keys():
            self.field_widgets[key].setText(labels[key])

    # ============================================================
    # Apply initial values
    # ============================================================
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        init_value = {
            DataManagementField.REPORT_PLANT: self._vm_data.include_plant,
            DataManagementField.REPORT_EXCITATION_FUNCTION: self._vm_data.include_excitation_function,
            DataManagementField.REPORT_CONTROLLER: self._vm_data.include_controller_configuration,
            DataManagementField.REPORT_PSO: self._vm_data.include_pso_configuration,
            DataManagementField.REPORT_BLOCK_DIAGRAM: self._vm_data.include_block_diagram,
            DataManagementField.REPORT_TIME_DOMAIN: self._vm_data.include_time_domain_plot,
            DataManagementField.REPORT_BODE: self._vm_data.include_bode_plot,
            DataManagementField.REPORT_TRANSFER_FUNCTION: self._vm_data.include_transfer_functions,
        }
        for key, value in init_value.items():
            self.field_widgets[key].setChecked(value)

        self._enable_report_section(False)

    # ============================================================
    # Applied theme
    # ============================================================
    def _on_theme_applied(self) -> None:
        """Update theme-dependent UI elements."""
        icon = self._load_icon(Icons.data_management, self._title_icon_size)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))

    # ============================================================
    # ViewModel change handlers
    # ============================================================
    def _on_pso_simulation_finished(self) -> None:
        """Update the PSO simulation finished UI elements."""
        self._enable_report_section(True)

    def _on_import_finished(self):
        self._info_banner.label.setText(self.tr("Import completed successfully"))
        self._info_banner.show_banner(5000)

    def _on_export_finished(self):
        self._info_banner.label.setText(self.tr("Export completed successfully"))
        self._info_banner.show_banner(5000)

    def _on_report_finished(self):
        self._info_banner.label.setText(self.tr("Report generated successfully"))
        self._info_banner.show_banner(5000)

    def _on_report_failed(self, message: str):
        # message comes from ViewModel → wrap in translated UI text
        self._error_banner.label.setText(message)
        self._error_banner.show_banner(7000)

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_export_requested(self, path: str) -> None:
        self._vm_data.save_project(path)

    def _on_import_requested(self, path: str) -> None:
        self._vm_data.load_project(path)

    def _on_export_report_requested(self, path: str) -> None:
        self._vm_data.generate_report(path)

    # ============================================================
    # Internal helpers
    # ============================================================
    def _enable_report_section(self, enable: bool) -> None:
        """Enable report section."""
        self._frm_report.setEnabled(enable)
        effect = self._frm_report.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(self._frm_report)
            self._frm_report.setGraphicsEffect(effect)
        effect.setOpacity(1.0 if enable else self._opacity_disabled)

    def _get_widget_bindings(self) -> list[ConnectSignalConfig]:
        def _wrapper(key: DataManagementField, attr: str) -> ConnectSignalConfig:
            return ConnectSignalConfig(
                key=key,
                signal_name="stateChanged",
                attr_name=attr,
                widget=self.field_widgets[key],
                kwargs={"value_type": bool},
                main_event_handler=self._on_widget_changed
            )

        return [
            _wrapper(DataManagementField.REPORT_PLANT, "_vm_data.include_plant"),
            _wrapper(DataManagementField.REPORT_EXCITATION_FUNCTION, "_vm_data.include_excitation_function"),
            _wrapper(DataManagementField.REPORT_CONTROLLER, "_vm_data.include_controller_configuration"),
            _wrapper(DataManagementField.REPORT_PSO, "_vm_data.include_pso_configuration"),
            _wrapper(DataManagementField.REPORT_BLOCK_DIAGRAM, "_vm_data.include_block_diagram"),
            _wrapper(DataManagementField.REPORT_TIME_DOMAIN, "_vm_data.include_time_domain_plot"),
            _wrapper(DataManagementField.REPORT_BODE, "_vm_data.include_bode_plot"),
            _wrapper(DataManagementField.REPORT_TRANSFER_FUNCTION, "_vm_data.include_transfer_functions"),
        ]

    def _get_vm_bindings(self) -> list[ConnectSignalConfig]:
        def _wrapper(key: DataManagementField, signal_name: str, attr: str) -> ConnectSignalConfig:
            return ConnectSignalConfig(
                key=key,
                signal_name=signal_name,
                attr_name=attr,
                widget=self._vm_data,
                kwargs={"field": self.field_widgets[key]},
                main_event_handler=self._on_vm_changed
            )

        return [
            _wrapper(
                DataManagementField.REPORT_PLANT,
                "includePlantChanged",
                "include_plant"
            ),
            _wrapper(
                DataManagementField.REPORT_EXCITATION_FUNCTION,
                "includeExcitationFunctionChanged",
                "include_excitation_function"
            ),
            _wrapper(
                DataManagementField.REPORT_CONTROLLER,
                "includeControllerConfigurationChanged",
                "include_controller_configuration"
            ),
            _wrapper(
                DataManagementField.REPORT_PSO,
                "includePsoConfigurationChanged",
                "include_pso_configuration"
            ),
            _wrapper(
                DataManagementField.REPORT_BLOCK_DIAGRAM,
                "includeBlockDiagramChanged",
                "include_block_diagram"
            ),
            _wrapper(
                DataManagementField.REPORT_TIME_DOMAIN,
                "includeTimeDomainPlotChanged",
                "include_time_domain_plot"
            ),
            _wrapper(
                DataManagementField.REPORT_BODE,
                "includeBodePlotChanged",
                "include_bode_plot"
            ),
            _wrapper(
                DataManagementField.REPORT_TRANSFER_FUNCTION,
                "includeTransferFunctionsChanged",
                "include_transfer_functions"
            ),
        ]
