from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget

from app_domain.ui_context import UiContext
from views import BaseView
from views.widgets import NavItem, NavigationWidget
from views.translations import NavLabels


class MainView(BaseView, QMainWindow):
    def __init__(self, ui_context: UiContext, nav_items: list[NavItem], view_factories: dict):
        QMainWindow.__init__(self)

        self._nav_items = nav_items
        self._view_factories = view_factories
        self._views = {}

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.setCentralWidget(central)

        self._nav = NavigationWidget(self._ui_context, self._nav_items, self)
        stack_frame, stack_layout = self._create_card()
        self._stack = QStackedWidget(stack_frame)
        stack_layout.addWidget(self._stack)

        layout.addWidget(self._nav)
        layout.addWidget(stack_frame, 1)

    # -------------------------------------------------
    # Signal / ViewModel Binding
    # -------------------------------------------------
    def _connect_signals(self) -> None:
        """Connect UI signals to event handlers."""
        self._nav.viewSelected.connect(self._switch_views)

    # -------------------------------------------------
    # ViewModel bindings (ViewModel → UI)
    # -------------------------------------------------
    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View update handlers."""

    # -------------------------------------------------
    # Translation
    # -------------------------------------------------
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self.setWindowTitle(self.tr("Control Optimizer"))

    # -------------------------------------------------
    # Apply initial values
    # -------------------------------------------------
    def _apply_init_value(self) -> None:
        """Apply initial values to all UI elements."""
        self._switch_views(NavLabels.PLANT)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------

    def _switch_views(self, key: NavLabels):
        if key not in self._views:
            view = self._view_factories[key]()
            self._views[key] = view
            self._stack.addWidget(view)

        self._stack.setCurrentWidget(self._views[key])
