from functools import partial

from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QSizePolicy,
    QFrame,
)

from app_domain.ui_context import UiContext
from app_types import NavItem, NavLabels, ThemeType
from views import ViewMixin
from views.resources import Icons

MENU_ICONS = {ThemeType.DARK: "menu_dark.svg", ThemeType.LIGHT: "menu_light.svg"}


class NavigationWidget(ViewMixin, QWidget):
    viewSelected = Signal(NavLabels)

    COLLAPSED_WIDTH = 70
    EXPANDED_WIDTH = 220
    BTN_SIZE = 40
    ICON_SIZE = int(BTN_SIZE * 0.8)
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

        ViewMixin.__init__(self, ui_context)

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

        self._toggle_btn.setIcon(self._load_icon(Icons.menu))
        self._toggle_btn.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))

        self._toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._toggle_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._toggle_btn.setObjectName("toggleBtn")

        toggle_row.addWidget(self._toggle_btn)
        toggle_row.addStretch()
        self._layout.addLayout(toggle_row)

        # Separate layouts for normal and bottom nav items
        top_layout = QVBoxLayout()
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 0)

        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

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

            self._field_widgets[item.key] = btn
            self._on_btn_clicked(self._init_item)

            # Add to top or bottom layout
            if getattr(item, "bottom", False):
                bottom_layout.addLayout(row)
            else:
                top_layout.addLayout(row)

        # Add top items
        self._layout.addLayout(top_layout)
        self._layout.addStretch()  # stretch pushes bottom items to the bottom
        # Add bottom items
        self._layout.addLayout(bottom_layout)

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        self._toggle_btn.clicked.connect(self._on_toggle)
        for key, btn in self._field_widgets.items():
            btn.clicked.connect(partial(self._on_btn_clicked, key=key))

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        for key, btn in self._field_widgets.items():
            text = self._enum_translation(key)
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
    def _on_theme_applied(self) -> None:
        self._toggle_btn.setIcon(self._load_icon(Icons.menu))

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

