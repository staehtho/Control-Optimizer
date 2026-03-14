import json
import logging
from pathlib import Path

from PySide6.QtCore import QSettings, QByteArray

from app_domain.controlsys import MySolver


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
        self._config_base_dir = Path(__file__).parent.parent / "config"
        self._logger.debug(f"Config base dir: {self._config_base_dir}")

        # Store base directory for i18n translation files
        self._i18n_base_dir = self._config_base_dir.parent / "i18n"
        self._logger.debug(f"i18n base dir: {self._i18n_base_dir}")

        # Store base directory for theme stylesheet files
        self._themes_base_dir = self._config_base_dir / "themes"
        self._logger.debug(f"Themes base dir: {self._themes_base_dir}")

        # File name for the QSettings INI file
        settings_file = "settings.ini"

        # Initialize QSettings with the INI file path
        self._settings = QSettings(
            str(self._config_base_dir / settings_file),
            QSettings.Format.IniFormat
        )

        # Load available language .qm from i18n/*.qm
        self._lang_cfg: dict[str, str] = self._load_language()

        # Load available theme stylesheets from config/themes/*.qss
        self._theme_cfg: dict[str, str] = self._load_themes()

        # Log initialization with info level
        self._logger.info(
            "SettingsModel initialized, config dir: %s, languages loaded: %s, themes loaded: %s",
            self._config_base_dir,
            list(self._lang_cfg.keys()),
            list(self._theme_cfg.keys()),
        )

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
    # UI themes
    # -------------------
    def get_themes_cfg(self) -> dict[str, str]:
        """Returns a mapping of available themes to their stylesheet content."""
        return dict(self._theme_cfg)

    def get_theme(self) -> str:
        """Returns the currently selected UI theme, defaults to 'dark'."""
        return str(self._settings.value("ui/theme", "dark", type=str))

    def set_theme(self, theme: str) -> None:
        """Sets the UI theme and logs the change."""
        if theme not in self._theme_cfg:
            raise ValueError(f"Unknown theme '{theme}'. Valid themes: {', '.join(self._theme_cfg.keys())}")
        self._logger.debug(f"Setting UI theme to '{theme}'")
        self._settings.setValue("ui/theme", theme.strip())

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
    # Solver Property
    # -------------------
    def get_solver(self) -> MySolver:
        """Returns the currently selected numerical solver from settings.

        Returns:
            MySolver: The currently selected solver. Defaults to MySolver.RK4 if no setting is found.
        """
        # Retrieve the solver name from QSettings, default to 'rk4'
        solver_name = str(
            self._settings.value("solver/solver", MySolver.RK4.name.lower(), type=str)
        )

        # Convert string back to Enum using uppercase (Enum keys are uppercase)
        return MySolver[solver_name.upper()]

    def set_solver(self, solver: MySolver) -> None:
        """Sets the current solver in QSettings and logs the change.

        Args:
            solver (MySolver): The solver to set (e.g., MySolver.RK4)
        """
        # Log the change for debugging
        self._logger.debug(f"Setting solver to '{solver.name.lower()}'")

        # Store the solver as lowercase string in QSettings
        self._settings.setValue("solver/solver", solver.name.lower())

    # -------------------
    # Time Step Property
    # -------------------
    def get_time_step(self) -> float:
        """Returns the current time step in seconds.
        Returns:
            float: Current time step in seconds.
        """
        return float(str(self._settings.value("solver/time_step", str(1e-4), type=str)))

    def set_time_step(self, time_step: float) -> None:
        """Sets the time step in seconds.
        Args:
            time_step (float): Time step in seconds.
        """
        self._logger.debug(f"Setting time step to '{time_step}'")
        self._settings.setValue("solver/time_step", str(time_step))

    # -------------------
    # Particle Property
    # -------------------
    def get_pso_particle(self) -> int:
        """Returns the number of PSO particles.
        Returns:
            int: Number of PSO particles.
        """
        return int(str(self._settings.value("pso/particle", 40, type=int)))

    def set_pso_particle(self, pso_particle: int) -> None:
        """Sets the number of PSO particles.
        Args:
            pso_particle (int): Number of PSO particles.
        """
        self._logger.debug(f"Setting PSO particle to '{pso_particle}'")
        self._settings.setValue("pso/particle", pso_particle)

    # -------------------
    # PSO Iteration Property
    # -------------------
    def get_pso_iterations(self) -> int:
        """Returns the number of PSO iterations.
        Returns:
            int: Number of PSO iterations.
        """
        return int(str(self._settings.value("pso/iterations", 14, type=int)))

    def set_pso_iterations(self, pso_iterations: int) -> None:
        """Sets the number of PSO iterations.
        Args:
            pso_iterations (int): Number of PSO iterations.
        """
        self._logger.debug(f"Setting PSO iterations to '{pso_iterations}'")
        self._settings.setValue("pso/iterations", pso_iterations)

    # -------------------
    # QM-File loader
    # -------------------
    def get_qm_file(self, lang_key: str) -> Path:
        """Returns the path to the QM file.
        Args:
            lang_key (str): Language of the QM file.
        """
        return self._i18n_base_dir / (self._lang_cfg.get(lang_key) + ".qm")

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

    def _load_language(self) -> dict[str, str]:
        lang_json = self._load_json(self._config_base_dir / "languages.json")
        languages: dict[str, str] = {}

        base_file_name = lang_json.get("base_file_name", "")
        for lang in lang_json.get("languages", []):
            languages.setdefault(lang, base_file_name + lang)

        self._logger.debug(f"Loaded languages from {lang_json}")
        return languages

    def _load_themes(self) -> dict[str, str]:
        """Loads all theme stylesheets from config/themes/*.qss."""
        if not self._themes_base_dir.exists():
            self._logger.error(f"Themes directory not found: {self._themes_base_dir}")
            raise FileNotFoundError(f"Themes directory not found: {self._themes_base_dir}")

        themes: dict[str, str] = {}
        for qss_file in sorted(self._themes_base_dir.glob("*.qss")):
            themes[qss_file.stem] = qss_file.read_text(encoding="utf-8")
            self._logger.debug(f"Loaded theme stylesheet from {qss_file}")

        if not themes:
            self._logger.error(f"No .qss theme files found in {self._themes_base_dir}")
            raise FileNotFoundError(f"No .qss theme files found in {self._themes_base_dir}")

        return themes
