from typing import Optional
from PySide6.QtWidgets import QFileDialog, QWidget
from PySide6.QtCore import Signal
from pathlib import Path

from .base_path_widget import BasePathWidget


class ImportPathWidget(BasePathWidget):
    importRequested = Signal(str)

    def __init__(self, file_filter: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(file_filter, parent)

    def retranslate(self):
        super().retranslate()
        self.action_btn.setText(self.tr("Import"))

    def choose_path(self):
        start_dir = str(Path.home() / "Downloads")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import File"),
            start_dir,
            self.file_filter
        )

        if not file_path:
            return

        self.path_edit.setText(file_path)
        self.pathSelected.emit(file_path)

        # auto‑import
        self.importRequested.emit(file_path)
