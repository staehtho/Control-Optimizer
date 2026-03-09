from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QCloseEvent

from app_domain.ui_context import UiContext
from viewmodels import PsoConfigurationViewModel
from views import BaseView
from views.widgets import NavItem, NavigationWidget
from views.translations import NavLabels


class MainView(BaseView, QMainWindow):
    def __init__(
            self,
            ui_context: UiContext,
            nav_items: list[NavItem],
            view_factories: dict,
            vm_pso: PsoConfigurationViewModel,
    ):
        QMainWindow.__init__(self)

        self._nav_items = nav_items
        self._view_factories = view_factories
        self._views = {}
        self._vm_pso = vm_pso
        self._has_pso_finished_once = self._vm_pso.get_pso_result() is not None

        BaseView.__init__(self, ui_context)

    # -------------------------------------------------
    # UI Initialization
    # -------------------------------------------------
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._nav = NavigationWidget(self._ui_context, self._nav_items, NavLabels.PLANT, self)
        stack_frame, stack_layout = self._create_plain_card(central)
        self._stack = QStackedWidget(stack_frame)
        stack_layout.addWidget(self._stack)

        stack_content = QWidget(central)
        stack_content_layout = QVBoxLayout(stack_content)
        stack_content_layout.setContentsMargins(0, 0, 0, 0)
        stack_content_layout.setSpacing(0)
        stack_content_layout.addWidget(stack_frame)

        scroll = self._wrap_in_scroll_area(stack_content)

        layout.addWidget(self._nav)
        layout.addWidget(scroll, 1)

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
        self._vm_pso.psoSimulationFinished.connect(self._on_vm_pso_simulation_finished)

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
        self._restore_window_state()
        self._apply_pso_gate()
        self._switch_views(NavLabels.PLANT)

    # -------------------------------------------------
    # ViewModel change handlers
    # -------------------------------------------------

    # -------------------------------------------------
    # UI event handlers
    # -------------------------------------------------

    def _switch_views(self, key: NavLabels):
        if not self._is_view_accessible(key):
            return

        self._stack.setUpdatesEnabled(False)
        if key not in self._views:
            view = self._view_factories[key](self._stack)
            self._views[key] = view
            self._stack.addWidget(view)

        self._stack.setCurrentWidget(self._views[key])
        self._stack.setUpdatesEnabled(True)

    def _is_view_accessible(self, key: NavLabels) -> bool:
        if self._has_pso_finished_once:
            return True

        return key not in (NavLabels.SIMULATION, NavLabels.EVALUATION)

    def _apply_pso_gate(self) -> None:
        views_active = self._has_pso_finished_once
        self._nav.set_nav_item_enabled(NavLabels.SIMULATION, views_active)
        self._nav.set_nav_item_enabled(NavLabels.EVALUATION, views_active)

    def _on_vm_pso_simulation_finished(self) -> None:
        if self._has_pso_finished_once:
            return

        self._has_pso_finished_once = True
        self._apply_pso_gate()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._ui_context.settings.set_window_geometry(self.saveGeometry())
        self._ui_context.settings.set_window_maximized(self.isMaximized())
        super().closeEvent(event)

    def _restore_window_state(self) -> None:
        geometry = self._ui_context.settings.get_window_geometry()
        if geometry is not None and not geometry.isEmpty():
            self.restoreGeometry(geometry)

        if self._ui_context.settings.get_window_maximized():
            self.showMaximized()
