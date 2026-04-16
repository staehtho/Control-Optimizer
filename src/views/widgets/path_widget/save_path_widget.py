from typing import Optional
from PySide6.QtWidgets import QFileDialog, QWidget, QMessageBox
from PySide6.QtCore import Signal
from pathlib import Path

from .base_path_widget import BasePathWidget


class SavePathWidget(BasePathWidget):
    exportRequested = Signal(str)

    def __init__(self, default_filename: str = "", file_filter: Optional[str] = None, parent: Optional[QWidget] = None):
        self.default_filename = default_filename
        super().__init__(file_filter, parent)

    def retranslate(self):
        super().retranslate()
        self.action_btn.setText(self.tr("Export"))

        # Default path
        default = Path.home() / "Downloads" / self.default_filename
        if not self.path_edit.text():
            self.path_edit.setText(str(default))

    def choose_path(self):
        start_dir = str(Path(self.path_edit.text()))

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save As"),
            start_dir,
            self.file_filter
        )

        if not file_path:
            return

        if file_path:
            if self.is_file_in_use(file_path):
                msg = QMessageBox(self)
                msg.setObjectName("OverwriteDialog")
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle(self.tr("File In Use"))
                msg.setText(self.tr("The file is currently open in another program. Please close it first."))

                msg.exec()
                return

        self.path_edit.setText(file_path)
        self.pathSelected.emit(file_path)

        # auto‑export
        self.exportRequested.emit(file_path)

    @staticmethod
    def is_file_in_use(path: str) -> bool:
        try:
            with open(path, "a"):
                return False
        except OSError:
            return True
