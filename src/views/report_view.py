from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QPushButton

from resources.resources import OUTPUT_DIR
from views.view_mixin import ViewMixin

if TYPE_CHECKING:
    from app_domain import UiContext
    from viewmodels.report_viewmodel import ReportViewModel


class ReportView(ViewMixin, QWidget):
    def __init__(self, ui_context: UiContext, vm_report: ReportViewModel, parent: QWidget = None) -> None:
        QWidget.__init__(self, parent)

        self._vm_report = vm_report

        ViewMixin.__init__(self, ui_context)

    def _init_ui(self) -> None:
        main_layout = self._create_page_layout()

        self._btn = QPushButton("Simulate", self)

        main_layout.addWidget(self._btn)

        self.setLayout(main_layout)

    def _connect_signals(self) -> None:
        self._btn.clicked.connect(self._on_btn_clicked)

    def _on_btn_clicked(self) -> None:
        self._vm_report.generate_report(OUTPUT_DIR / "report.pdf")
