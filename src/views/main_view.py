from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget

from viewmodels import LanguageViewModel
from views import BaseView
from views.widgets import NavItem, NavigationWidget
from views.translations import NavLabels


class MainView(BaseView, QMainWindow):
    def __init__(self, vm_lang: LanguageViewModel, nav_items: list[NavItem], view_factories: dict):
        QMainWindow.__init__(self)

        self._nav_items = nav_items
        self._view_factories = view_factories
        self._views = {}

        BaseView.__init__(self, vm_lang)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        self._nav = NavigationWidget(self._vm_lang, self._nav_items, self)
        self._stack = QStackedWidget()

        layout.addWidget(self._nav)
        layout.addWidget(self._stack)

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
