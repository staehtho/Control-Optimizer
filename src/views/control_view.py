from PySide6.QtWidgets import QWidget


from viewmodels import LanguageViewModel, ControllerViewModel
from .base_view import BaseView

class ControllerModel(BaseView, QWidget):
    def __init__(self, vm_lang: LanguageViewModel, vm_controller: ControllerViewModel):
        QWidget.__init__(self)

        self._vm_controller = vm_controller

        BaseView.__init__(self, vm_lang)

    def _init_ui(self) -> None:
        """Create and configure UI elements (widgets, layouts, etc.)."""
        ...

    def _connect_signals(self) -> None:
        """Connect UI signals (buttons, input fields, etc.) to handlers."""
        ...

    def _bind_vm(self) -> None:
        """Bind ViewModel signals to View updates (model → view)."""
        ...

    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        ...