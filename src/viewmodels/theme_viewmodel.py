import re
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor

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
        self._theme_text_colors: dict[ThemeType, QColor] = {}
        self._theme_background_colors: dict[ThemeType, QColor] = {}
        self._current_theme: ThemeType | None = None
        self._build_theme_cache()

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

    def get_theme_stylesheet(self, theme: ThemeType | str | None = None) -> str | None:
        theme_type = self._resolve_theme(theme)
        if theme_type is None:
            return None
        return self._theme_cfg.get(theme_type)

    def get_theme_text_color(self) -> QColor:
        return self._theme_text_colors.get(self._current_theme)

    def get_theme_background_color(self) -> QColor:
        return self._theme_background_colors.get(self._current_theme)

    def _resolve_theme(self, theme: ThemeType | str | None) -> ThemeType | None:
        if theme is None:
            return self._current_theme
        try:
            return theme if isinstance(theme, ThemeType) else ThemeType(theme)
        except ValueError:
            self.logger.warning(f"Unknown theme '{theme}' -> ignored")
            return None

    def _build_theme_cache(self) -> None:
        self._theme_text_colors.clear()
        self._theme_background_colors.clear()
        for theme_key, stylesheet in self._theme_cfg.items():
            background = self._extract_widget_background_color(stylesheet)
            font = self._extract_widget_font_color(stylesheet)
            if font is not None:
                self._theme_text_colors[theme_key] = font
            if background is not None:
                self._theme_background_colors[theme_key] = background

    @staticmethod
    def _extract_widget_background_color(stylesheet: str) -> QColor | None:
        # Prefer the view root background when defined.
        match = re.search(
            r"QWidget\s*#\s*viewRoot\s*\{[^}]*\bbackground(?:-color)?\s*:\s*([^;]+);",
            stylesheet,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match is None:
            match = re.search(
                r"QWidget\s*\{[^}]*\bbackground(?:-color)?\s*:\s*([^;]+);",
                stylesheet,
                flags=re.IGNORECASE | re.DOTALL,
            )
        if match is None:
            return None
        color = QColor(match.group(1).strip())
        return color if color.isValid() else None

    @staticmethod
    def _extract_widget_font_color(stylesheet: str) -> QColor | None:
        match = re.search(
            r"QWidget\s*\{[^}]*\bcolor\s*:\s*([^;]+);",
            stylesheet,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match is None:
            return None
        color = QColor(match.group(1).strip())
        return color if color.isValid() else None

    def get_svg_color_map(self) -> dict[str, str]:
        return {
            "#ffffff": self._theme_background_colors.get(self._current_theme).name(),
            "#000000": self._theme_text_colors.get(self._current_theme).name()
        }
