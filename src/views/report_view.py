from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout

from app_types import ReportField
from resources.resources import Icons
from views.widgets.path_widget import SavePathWidget, ImportPathWidget
from views.view_mixin import ViewMixin

if TYPE_CHECKING:
    from app_domain import UiContext
    from viewmodels.report_viewmodel import ReportViewModel
    from views.widgets import SectionFrame


class ReportView(ViewMixin, QWidget):
    def __init__(self, ui_context: UiContext, vm_report: ReportViewModel, parent: QWidget = None) -> None:
        QWidget.__init__(self, parent)

        self._vm_report = vm_report

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

        self.setLayout(main_layout)

    def _create_export_import_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card()

        # export
        default_filename = f"control_optimizer_export_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        file_filter = self.tr("JSON Files (*.json)")

        export_widget = SavePathWidget(default_filename, file_filter=file_filter, parent=self)
        layout.addWidget(export_widget)
        self.field_widgets.setdefault(ReportField.EXPORT, export_widget)

        # import
        import_widget = ImportPathWidget(file_filter=file_filter, parent=self)
        layout.addWidget(import_widget)
        self.field_widgets.setdefault(ReportField.IMPORT, import_widget)

        return frame

    def _create_report_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card()

        default_filename = f"control_optimizer_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        file_filter = self.tr("PDF Files (*.pdf)")
        # TODO: creat check box to select section
        save_report_widget = SavePathWidget(default_filename, file_filter=file_filter, parent=self)
        layout.addWidget(save_report_widget)
        self.field_widgets.setdefault(ReportField.REPORT, save_report_widget)

        return frame

    # ============================================================
    # Signal / ViewModel Binding
    # ============================================================
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self.field_widgets[ReportField.EXPORT].exportRequested.connect(self._on_export_requested)
        self.field_widgets[ReportField.IMPORT].importRequested.connect(self._on_import_requested)
        self.field_widgets[ReportField.REPORT].exportRequested.connect(self._on_export_report_requested)

    # ============================================================
    # ViewModel bindings (ViewModel -> UI)
    # ============================================================
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        ...

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self.tr("Data Management"))
        self._frm_export_import.setText(self.tr("Import and Export App Data"))
        self._frm_report.setText(self.tr("Create Report"))

        for key in (ReportField.EXPORT, ReportField.IMPORT, ReportField.REPORT):
            self.field_widgets[key].retranslate()

    # ============================================================
    # UI event handlers
    # ============================================================
    def _on_export_requested(self, path: str) -> None:
        self._vm_report.save_project(path)

    def _on_import_requested(self, path: str) -> None:
        self._vm_report.load_project(path)

    def _on_export_report_requested(self, path: str) -> None:
        self._vm_report.generate_report(path)
