from PySide6.QtCore import QObject, Signal, Slot

from models import SettingsModel
from .base_viewmodel import BaseViewModel


class ThemeViewModel(BaseViewModel):
    """ViewModel that manages app theme selection and persistence."""

    themeChanged = Signal(str)

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        super().__init__(parent)

        self._settings = settings
        self._theme_cfg = settings.get_themes_cfg()
        self._current_theme: str = ""

        # Initialize theme from persisted settings.
        self.set_theme(self._settings.get_theme())

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    @Slot(str)
    def set_theme(self, theme: str) -> None:
        """Set and persist the requested theme."""
        if theme not in self._theme_cfg:
            self.logger.warning(f"Unknown theme '{theme}' -> ignored")
            return

        if theme == self._current_theme:
            self.logger.debug(f"Theme '{theme}' already active -> no change")
            return

        self.logger.debug(f"Changing theme from '{self._current_theme}' to '{theme}'")
        self._current_theme = theme
        self._settings.set_theme(theme)
        self.themeChanged.emit(theme)

    current_theme = BaseViewModel._logged_property(
        attribute="_current_theme",
        notify_signal="themeChanged",
        property_type=str,
        read_only=True,
    )

    def get_theme_cfg(self) -> dict[str, str]:
        return dict(self._theme_cfg)
