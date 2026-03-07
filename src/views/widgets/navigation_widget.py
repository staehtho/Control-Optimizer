from dataclasses import dataclass
from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSizePolicy

from app_domain.ui_context import UiContext
from views import BaseView
from views.translations import NavLabels


@dataclass
class NavItem:
    key: NavLabels
    icon: str


class NavigationWidget(BaseView, QWidget):
    viewSelected = Signal(NavLabels)

    def __init__(self, ui_context: UiContext, nav_items: list[NavItem], parent: QWidget = None):
        QWidget.__init__(self, parent)

        self._nav_items = nav_items
        self._collapsed = False

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        self.setFixedWidth(220)
        self.setObjectName("card")
        self._btn_size = 30

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 14, 12, 14)
        self._layout.setSpacing(8)
        self.setLayout(self._layout)
        self._toggle_btn = QPushButton(self)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setCheckable(False)
        self._toggle_btn.setFixedSize(self._btn_size, self._btn_size)
        self._layout.insertWidget(0, self._toggle_btn)

        for item in self._nav_items:
            btn = QPushButton(self)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(self._btn_size)

            self._layout.addWidget(btn)
            self._field_widgets[item.key] = btn

        self._layout.addStretch()
        self._update_toggle_button()

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._toggle_btn.clicked.connect(self._on_toggle)

        for key, btn in self._field_widgets.items():
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
        for key, btn in self._field_widgets.items():
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
            for btn in self._field_widgets.values():
                btn.setText("")
        else:
            self.setFixedWidth(220)
            for item in self._nav_items:
                self._field_widgets[item.key].setText(self._enum_translation(NavLabels).get(item.key))
        self._update_toggle_button()

    def _update_toggle_button(self) -> None:
        self._toggle_btn.setText(">" if self._collapsed else "<")
        self._layout.setAlignment(self._toggle_btn,
                                  Qt.AlignmentFlag.AlignRight if not self._collapsed else Qt.Alignment())

    def _on_btn_clicked(self, key: NavLabels):
        for k, btn in self._field_widgets.items():
            btn.setChecked(k == key)

        self.viewSelected.emit(key)

    def set_nav_item_enabled(self, key: NavLabels, enabled: bool) -> None:
        btn = self._field_widgets.get(key)
        if btn is None:
            return
        btn.setEnabled(enabled)

    def is_nav_item_enabled(self, key: NavLabels) -> bool:
        btn = self._field_widgets.get(key)
        if btn is None:
            return False
        return btn.isEnabled()
