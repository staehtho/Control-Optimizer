from typing import Optional
from PySide6.QtWidgets import QFileDialog, QWidget, QMessageBox, QPushButton
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

        if file_path:
            self.path_edit.setText(file_path)
            self.pathSelected.emit(file_path)

    def _emit_action(self):
        path = self.path_edit.text().strip()
        if not path:
            return

        target = Path(path)

        if target.exists():
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(self.tr("File Exists"))
            msg.setText(self.tr("The file already exists. Do you want to overwrite it?"))

            # Create translated buttons
            btn_ok = QPushButton(self.tr("OK"))
            btn_cancel = QPushButton(self.tr("Cancel"))

            # Add buttons manually
            msg.addButton(btn_ok, QMessageBox.ButtonRole.AcceptRole)
            msg.addButton(btn_cancel, QMessageBox.ButtonRole.RejectRole)

            # Ensure same width
            w = max(btn_ok.sizeHint().width(), btn_cancel.sizeHint().width())
            btn_ok.setFixedWidth(w)
            btn_cancel.setFixedWidth(w)

            result = msg.exec()

            if msg.clickedButton() != btn_ok:
                return  # user canceled

        # User confirmed or file does not exist
        self.exportRequested.emit(path)
