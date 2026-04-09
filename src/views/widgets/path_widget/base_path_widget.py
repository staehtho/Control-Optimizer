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

        self.browse_btn = QPushButton()
        self.action_btn = QPushButton()  # Save or Import depending on subclass

        row = QHBoxLayout(self)
        row.addWidget(self.path_edit)
        row.addWidget(self.browse_btn)
        row.addWidget(self.action_btn)

        # Equal button sizes
        self.browse_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.action_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.browse_btn.clicked.connect(self.choose_path)
        self.action_btn.clicked.connect(self._emit_action)

    def retranslate(self):
        self.browse_btn.setText(self.tr("Browse…"))

        # Filter translation
        if self.file_filter_raw:
            self.file_filter = self.tr(self.file_filter_raw)
        else:
            self.file_filter = self.tr("All Files (*)")

    # --- Methods subclasses MUST override ---
    def choose_path(self):
        raise NotImplementedError

    def _emit_action(self):
        raise NotImplementedError
