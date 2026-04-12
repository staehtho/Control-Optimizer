from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy
)
from PySide6.QtCore import Signal


class BasePathWidget(QWidget):
    pathSelected = Signal(str)  # emitted when user chooses a path

    def __init__(self, file_filter: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.file_filter_raw: str | None = file_filter
        self.file_filter: str = ""

        self._build_ui()
        self.retranslate()

    def _build_ui(self):
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.mousePressEvent = lambda event: self.choose_path()

        self.action_btn = QPushButton()

        row = QHBoxLayout(self)
        row.addWidget(self.path_edit, 5)
        row.addWidget(self.action_btn, 1)

        self.action_btn.clicked.connect(self.choose_path)

    def retranslate(self):
        # Filter translation
        if self.file_filter_raw:
            self.file_filter = self.tr(self.file_filter_raw)
        else:
            self.file_filter = self.tr("All Files (*)")

    # --- Methods subclasses MUST override ---
    def choose_path(self):
        raise NotImplementedError
