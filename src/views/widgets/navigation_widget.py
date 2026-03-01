from dataclasses import dataclass
from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QPushButton, QSizePolicy

from viewmodels import LanguageViewModel
from views import BaseView
from views.translations import NavLabels


@dataclass
class NavItem:
    key: NavLabels
    icon: str


class NavigationWidget(BaseView, QWidget):
    viewSelected = Signal(NavLabels)

    def __init__(self, vm_lang: LanguageViewModel, nav_items: list[NavItem], parent: QWidget = None):
        QWidget.__init__(self, parent)

        self._nav_items = nav_items
        self._collapsed = False

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        self.setFixedWidth(220)

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(10, 20, 10, 20)
        self._layout.setSpacing(6)
        self.setLayout(self._layout)

        self._toggle_btn = QPushButton("☰")
        self._layout.insertWidget(0, self._toggle_btn)

        for item in self._nav_items:
            btn = QPushButton()
            # btn.setIcon(QIcon(item.icon))
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            self._layout.addWidget(btn)
            self._widgets[item.key] = btn

        self._layout.addStretch()

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._toggle_btn.clicked.connect(self._on_toggle)

        for key, btn in self._widgets.items():
            btn.clicked.connect(partial(self._on_btn_clicked, key=key))

    # -------------------------------------------------
    # ViewModel bindings (ViewModel -> UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""
        ...

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        for key, btn in self._widgets.items():
            btn.setText(self._enum_translation(NavLabels).get(key))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        ...

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------
    def _on_toggle(self) -> None:
        self._collapsed = not self._collapsed

        if self._collapsed:
            self.setFixedWidth(70)
            for btn in self._widgets.values():
                btn.setText("")
        else:
            self.setFixedWidth(220)
            for item in self._nav_items:
                self._widgets[item.key].setText(self._enum_translation(NavLabels).get(item.key))

    def _on_btn_clicked(self, key: NavLabels):
        for k, btn in self._widgets.items():
            btn.setChecked(k == key)

        self.viewSelected.emit(key)
