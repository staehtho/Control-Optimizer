from dataclasses import dataclass
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QSizePolicy,
    QFrame,
)

from app_domain.ui_context import UiContext
from views import BaseView
from views.translations import NavLabels


@dataclass
class NavItem:
    key: NavLabels
    icon: str


class NavigationWidget(BaseView, QWidget):
    viewSelected = Signal(NavLabels)

    COLLAPSED_WIDTH = 70
    EXPANDED_WIDTH = 220
    BTN_SIZE = 30
    ICON_SIZE = 20
    ACTIVE_BAR_WIDTH = 4

    def __init__(self, ui_context: UiContext, nav_items: list[NavItem], init_item: NavLabels,
                 parent: QWidget | None = None):
        QWidget.__init__(self, parent)

        self._vm_theme = ui_context.vm_theme
        self._nav_items = nav_items
        self._init_item = init_item

        self._collapsed = False
        self._field_widgets: dict[NavLabels, QToolButton] = {}
        self._active_bar_frames: dict[NavLabels, QFrame] = {}

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.setObjectName("card")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Toggle button row
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(self.ACTIVE_BAR_WIDTH, 5, 0, 0)
        toggle_row.setSpacing(0)

        self._toggle_btn = QToolButton(self)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFixedSize(self.BTN_SIZE, self.BTN_SIZE)
        self._toggle_btn.setIcon(self._load_icon("menu.svg"))
        self._toggle_btn.setIconSize(QSize(18, 18))
        self._toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._toggle_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._toggle_btn.setObjectName("toggleBtn")

        toggle_row.addWidget(self._toggle_btn)
        toggle_row.addStretch()
        self._layout.addLayout(toggle_row)

        # Navigation buttons
        for item in self._nav_items:
            row = QHBoxLayout()
            row.setContentsMargins(0, 5, 0, 0)
            row.setSpacing(0)

            # Active page bar
            bar = QFrame(self)
            bar.setFixedWidth(self.ACTIVE_BAR_WIDTH)
            bar.setStyleSheet("background-color: transparent;")
            row.addWidget(bar)
            self._active_bar_frames[item.key] = bar

            # Nav button
            btn = QToolButton(self)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(self.BTN_SIZE)
            btn.setIcon(self._load_icon(item.icon))
            btn.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet("text-align:left; padding-left:6px;")
            btn.setObjectName(f"navBtn_{item.key}")

            row.addWidget(btn)
            self._layout.addLayout(row)

            self._field_widgets[item.key] = btn
            self._on_btn_clicked(self._init_item)

        self._layout.addStretch()

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        self._toggle_btn.clicked.connect(self._on_toggle)
        for key, btn in self._field_widgets.items():
            btn.clicked.connect(partial(self._on_btn_clicked, key=key))

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self):
        self._vm_theme.themeChanged.connect(self._on_vm_theme_changed)

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        translations = self._enum_translation(NavLabels)
        for key, btn in self._field_widgets.items():
            text = translations.get(key)
            if self._collapsed:
                btn.setText("")
                btn.setToolTip(text)
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            else:
                btn.setText(text)
                btn.setToolTip("")
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    # -------------------------------------------------
    # Animation
    # -------------------------------------------------
    def _animate_sidebar(self, target_width: int) -> None:
        self._animation = QPropertyAnimation(self, b"minimumWidth")
        self._animation.setDuration(150)
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target_width)
        self._animation.start()
        self.setMaximumWidth(target_width)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------
    def _on_vm_theme_changed(self) -> None:
        self._toggle_btn.setIcon(self._load_icon("menu.svg"))

        for item in self._nav_items:
            btn = self._field_widgets[item.key]
            btn.setIcon(self._load_icon(item.icon))

    # -------------------------------------------------
    # Event Handlers
    # -------------------------------------------------
    def _on_toggle(self) -> None:
        self._collapsed = not self._collapsed
        width = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        self._animate_sidebar(width)
        self._retranslate()

    def _on_btn_clicked(self, key: NavLabels) -> None:
        for k, btn in self._field_widgets.items():
            checked = k == key
            btn.setChecked(checked)
            self._active_bar_frames[k].setStyleSheet(
                f"background-color: {'#2563eb' if checked else 'transparent'};"
            )
        self.viewSelected.emit(key)

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def set_nav_item_enabled(self, key: NavLabels, enabled: bool) -> None:
        btn = self._field_widgets.get(key)
        if btn:
            btn.setEnabled(enabled)

    def is_nav_item_enabled(self, key: NavLabels) -> bool:
        btn = self._field_widgets.get(key)
        return btn.isEnabled() if btn else False

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------
    def _load_icon(self, icon: str) -> QIcon:
        icon_path = Path("icons") / self._vm_theme.current_theme.value / icon
        return QIcon(str(icon_path.resolve()))
