from PySide6.QtCore import QSettings, QByteArray

from pathlib import Path
import json
import logging

class SettingsModel:
    """Model handling application settings with persistent storage and logging.

    This model manages UI language, window state (geometry, maximized),
    and loads language configuration from JSON. It inherits LoggingService
    to provide centralized logging.
    """

    def __init__(self):
        """Initializes SettingsModel and loads configurations."""
        self._logger = logging.getLogger(f"Model.{self.__class__.__name__}")

        # Store base directory for config files
        self._config_base_dir = Path().resolve() / "config"

        # File name for the QSettings INI file
        settings_file = "settings.ini"

        # Initialize QSettings with the INI file path
        self._settings = QSettings(
            str(self._config_base_dir / settings_file),
            QSettings.IniFormat
        )

        # Load language configuration JSON
        self._languages_cfg: dict = self._load_json(
            self._config_base_dir / "languages.json"
        ).get("languages", {})

        # Log initialization with info level
        self._logger.info(f"SettingsModel initialized, config dir: {self._config_base_dir}, languages loaded: {list(self._languages_cfg.keys())}")

    # -------------------
    # Base directory and language config accessors
    # -------------------
    def get_config_base_dir(self) -> Path:
        """Returns the base directory for config files."""
        return self._config_base_dir

    def get_languages_cfg(self) -> dict:
        """Returns the dictionary of available language configurations."""
        return self._languages_cfg

    # -------------------
    # UI language
    # -------------------
    def get_language(self) -> str:
        """Returns the currently selected UI language, defaults to 'en'."""
        return str(self._settings.value("ui/language", "en", type=str))

    def set_language(self, lang: str) -> None:
        """Sets the UI language and logs the change.

        Args:
            lang (str): Language code to set (e.g., 'en', 'de').
        """
        self._logger.debug(f"Setting UI language to '{lang}'")
        self._settings.setValue("ui/language", lang)

    # -------------------
    # Window state
    # -------------------
    def get_window_geometry(self) -> QByteArray | None:
        """Returns the stored window geometry as QByteArray or None if not set."""
        value = self._settings.value("window/geometry", type=QByteArray)
        if isinstance(value, QByteArray):
            return value
        return None

    def set_window_geometry(self, geometry: QByteArray) -> None:
        """Stores the window geometry and logs the action.

        Args:
            geometry (QByteArray): Window geometry data from QMainWindow.saveGeometry().
        """
        self._logger.debug(f"Setting window geometry to {geometry}")
        self._settings.setValue("window/geometry", geometry)

    def get_window_maximized(self) -> bool:
        """Returns True if the window was maximized, False otherwise."""
        return bool(self._settings.value("window/maximized", type=bool))

    def set_window_maximized(self, maximize: bool) -> None:
        """Stores the maximized state of the window and logs the change.

        Args:
            maximize (bool): True if window should be maximized, else False.
        """
        self._logger.debug(f"Setting window maximized to {maximize}")
        self._settings.setValue("window/maximized", maximize)

    # -------------------
    # JSON loader helper
    # -------------------
    def _load_json(self, path: Path | str) -> dict:
        """Loads a JSON file and returns its contents as a dictionary.

        Args:
            path (Path | str): Path to the JSON file.

        Returns:
            dict: Parsed JSON contents.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
        """
        path = Path(path)
        if not path.is_absolute():
            path = self._config_base_dir / path

        if not path.exists():
            self._logger.error(f"JSON file not found: {path}")
            raise FileNotFoundError(f"JSON file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            self._logger.debug(f"Loaded JSON from {path}")
            return json.load(f)
