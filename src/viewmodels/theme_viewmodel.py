from PySide6.QtCore import QObject, Signal, Slot

from models import SettingsModel
from utils import LoggedProperty
from app_types import ThemeType
from .base_viewmodel import BaseViewModel


class ThemeViewModel(BaseViewModel):
    """ViewModel that manages app theme selection and persistence."""

    themeChanged = Signal(object)

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        super().__init__(parent)

        self._settings = settings
        raw_cfg = settings.get_themes_cfg()
        self._theme_cfg: dict[ThemeType, str] = {ThemeType(key): value for key, value in raw_cfg.items()}
        self._current_theme: ThemeType | None = None

        # Initialize theme from persisted settings.
        self.set_theme(self._settings.get_theme())

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    @Slot(object)
    def set_theme(self, theme: ThemeType | str) -> None:
        """Set and persist the requested theme."""
        try:
            theme_type = theme if isinstance(theme, ThemeType) else ThemeType(theme)
        except ValueError:
            self.logger.warning(f"Unknown theme '{theme}' -> ignored")
            return

        if theme_type == self._current_theme:
            self.logger.debug(f"Theme '{theme_type.value}' already active -> no change")
            return

        previous = self._current_theme.value if self._current_theme is not None else None
        self.logger.debug(f"Changing theme from '{previous}' to '{theme_type.value}'")
        self._current_theme = theme_type
        self._settings.set_theme(theme_type.value)
        self.themeChanged.emit(theme_type)

    current_theme = LoggedProperty(
        path="_current_theme",
        typ=object,
        read_only=True,
    )

    def get_theme_cfg(self) -> dict[ThemeType, str]:
        return dict(self._theme_cfg)

