import json
import logging
from pathlib import Path

from PySide6.QtCore import QSettings, QByteArray, Qt, QObject, Property, Slot
from PySide6.QtGui import QGuiApplication

from app_domain.controlsys import MySolver
from app_types import PsoHyperparameters
from resources.resources import SETTINGS_DIR, CONFIG_DIR, THEMES_DIR, I18N_DIR


class SettingsModel(QObject):
    """Model handling application settings with persistent storage and logging.

    This model manages UI language, window state (geometry, maximized),
    and loads language configuration from JSON. It inherits LoggingService
    to provide centralized logging.
    """

    def __init__(self):
        """Initializes SettingsModel and loads configurations."""
        super().__init__()
        self._logger = logging.getLogger(f"Model.{self.__class__.__name__}")

        # Store base directory for config files
        self._config_base_dir = CONFIG_DIR
        self._logger.debug(f"Config base dir: {self._config_base_dir}")

        # Store base directory for i18n translation files
        self._i18n_base_dir = I18N_DIR
        self._logger.debug(f"i18n base dir: {self._i18n_base_dir}")

        # Store base directory for theme stylesheet files
        self._themes_base_dir = THEMES_DIR
        self._logger.debug(f"Themes base dir: {self._themes_base_dir}")

        # File name for the QSettings INI file
        settings_file = "settings.ini"

        # Initialize QSettings with the INI file path
        # Initialize QSettings with the INI file path
        self._settings = QSettings(
            str(SETTINGS_DIR / settings_file),
            QSettings.Format.IniFormat
        )

        # Load available language translators from config
        self._languages, self._translator_cfg = self._load_language()

        # Load available theme stylesheets from config/themes/*.qss
        self._theme_cfg: dict[str, str] = self._load_themes()

        # Log initialization with info level
        self._logger.info(
            "SettingsModel initialized, config dir: %s, languages loaded: %s, themes loaded: %s",
            self._config_base_dir,
            list(self._languages),
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
        """Returns the selected UI theme or the current system theme if unset."""
        if self._settings.contains("ui/theme"):
            return str(self._settings.value("ui/theme", type=str))
        return self._get_system_theme()

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
    # Navigation state
    # -------------------
    def get_nav_collapsed(self) -> bool:
        """Returns True if the navigation is collapsed, False otherwise."""
        return bool(self._settings.value("ui/nav_collapsed", False, type=bool))

    def set_nav_collapsed(self, collapsed: bool) -> None:
        """Stores the navigation collapsed state and logs the change.

        Args:
            collapsed (bool): True if nav should be collapsed, else False.
        """
        self._logger.debug(f"Setting nav collapsed to {collapsed}")
        self._settings.setValue("ui/nav_collapsed", collapsed)

    # -------------------
    # Solver Property
    # -------------------
    def _get_solver(self) -> MySolver:
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

    def _set_solver(self, solver: MySolver) -> None:
        """Sets the current solver in QSettings and logs the change.

        Args:
            solver (MySolver): The solver to set (e.g., MySolver.RK4)
        """
        # Log the change for debugging
        self._logger.debug(f"Setting solver to '{solver.name.lower()}'")

        # Store the solver as lowercase string in QSettings
        self._settings.setValue("solver/solver", solver.name.lower())

    solver: MySolver = Property(MySolver, _get_solver, _set_solver)

    # -------------------
    # Time Step Property
    # -------------------
    def _get_time_step(self) -> float:
        """Returns the current time step in seconds.
        Returns:
            float: Current time step in seconds.
        """
        return float(str(self._settings.value("solver/time_step", str(1e-4), type=str)))

    def _set_time_step(self, time_step: float) -> None:
        """Sets the time step in seconds.
        Args:
            time_step (float): Time step in seconds.
        """
        self._logger.debug(f"Setting time step to '{time_step}'")
        self._settings.setValue("solver/time_step", str(time_step))

    time_step: float = Property(float, _get_time_step, _set_time_step)

    # -------------------
    # PSO parameters
    # -------------------
    def _get_pso_swarm_size(self) -> int:
        """Returns the swarm size."""
        return int(str(self._settings.value("pso/swarm_size", 40, type=int)))

    def _set_pso_swarm_size(self, swarm_size: int) -> None:
        """Sets the swarm size."""
        self._logger.debug(f"Setting PSO swarm_size to '{swarm_size}'")
        self._settings.setValue("pso/swarm_size", swarm_size)

    pso_swarm_size: int = Property(int, _get_pso_swarm_size, _set_pso_swarm_size)

    def _get_pso_repeat_runs(self) -> int:
        """Returns the number of PSO runs."""
        return int(str(self._settings.value("pso/repeat_runs", 14, type=int)))

    def _set_pso_repeat_runs(self, repeat_runs: int) -> None:
        """Sets the number of PSO runs."""
        self._logger.debug(f"Setting PSO repeat_runs to '{repeat_runs}'")
        self._settings.setValue("pso/repeat_runs", repeat_runs)

    pso_repeat_runs: int = Property(int, _get_pso_repeat_runs, _set_pso_repeat_runs)

    def _get_pso_randomness(self) -> float:
        """Returns the PSO randomness factor."""
        return float(str(self._settings.value("pso/randomness", 1.0, type=float)))

    def _set_pso_randomness(self, randomness: float) -> None:
        """Sets the PSO randomness factor."""
        self._logger.debug(f"Setting PSO randomness to '{randomness}'")
        self._settings.setValue("pso/randomness", randomness)

    pso_randomness: float = Property(float, _get_pso_randomness, _set_pso_randomness)

    def _get_pso_u1(self) -> float:
        """Returns the PSO cognitive coefficient."""
        return float(str(self._settings.value("pso/u1", 1.49, type=float)))

    def _set_pso_u1(self, u1: float) -> None:
        """Sets the PSO cognitive coefficient."""
        self._logger.debug(f"Setting PSO u1 to '{u1}'")
        self._settings.setValue("pso/u1", u1)

    pso_u1: float = Property(float, _get_pso_u1, _set_pso_u1)

    def _get_pso_u2(self) -> float:
        """Returns the PSO social coefficient."""
        return float(str(self._settings.value("pso/u2", 1.49, type=float)))

    def _set_pso_u2(self, u2: float) -> None:
        """Sets the PSO social coefficient."""
        self._logger.debug(f"Setting PSO u2 to '{u2}'")
        self._settings.setValue("pso/u2", u2)

    pso_u2: float = Property(float, _get_pso_u2, _set_pso_u2)

    def _get_pso_initial_range_start(self) -> float:
        """Returns the initial PSO value range."""
        return float(str(self._settings.value("pso/initial_range_start", 0.1, type=float)))

    def _set_pso_initial_range_start(self, initial_range_start: float) -> None:
        """Sets the initial PSO value range."""
        self._logger.debug(f"Setting PSO initial_range to '{initial_range_start}'")
        self._settings.setValue("pso/initial_range_start", initial_range_start)

    pso_initial_range_start: float = Property(float, _get_pso_initial_range_start, _set_pso_initial_range_start)

    def _get_pso_initial_range_end(self) -> float:
        """Returns the initial PSO value range."""
        return float(str(self._settings.value("pso/initial_range_end", 1.1, type=float)))

    def _set_pso_initial_range_end(self, initial_range_end: float) -> None:
        """Sets the initial PSO value range."""
        self._logger.debug(f"Setting PSO initial_range to '{initial_range_end}'")
        self._settings.setValue("pso/initial_range_end", initial_range_end)

    pso_initial_range_end: float = Property(float, _get_pso_initial_range_end, _set_pso_initial_range_end)

    def _get_pso_initial_swarm_span(self) -> int:
        """Returns the initial PSO swarm span."""
        return int(str(self._settings.value("pso/initial_swarm_span", 2000, type=int)))

    def _set_pso_initial_swarm_span(self, initial_swarm_span: int) -> None:
        """Sets the initial PSO swarm span."""
        self._logger.debug(f"Setting PSO initial_swarm_span to '{initial_swarm_span}'")
        self._settings.setValue("pso/initial_swarm_span", initial_swarm_span)

    pso_initial_swarm_span: int = Property(int, _get_pso_initial_swarm_span, _set_pso_initial_swarm_span)

    def _get_pso_min_neighbors_fraction(self) -> float:
        """Returns the minimum PSO neighbors fraction."""
        return float(str(self._settings.value("pso/min_neighbors_fraction", 0.25, type=float)))

    def _set_pso_min_neighbors_fraction(self, min_neighbors_fraction: float) -> None:
        """Sets the minimum PSO neighbors fraction."""
        self._logger.debug(f"Setting PSO min_neighbors_fraction to '{min_neighbors_fraction}'")
        self._settings.setValue("pso/min_neighbors_fraction", min_neighbors_fraction)

    pso_min_neighbors_fraction: float = (
        Property(float, _get_pso_min_neighbors_fraction, _set_pso_min_neighbors_fraction)
    )

    def _get_pso_max_stall(self) -> int:
        """Returns the maximum PSO stall count."""
        return int(str(self._settings.value("pso/max_stall", 15, type=int)))

    def _set_pso_max_stall(self, max_stall: int) -> None:
        """Sets the maximum PSO stall count."""
        self._logger.debug(f"Setting PSO max_stall to '{max_stall}'")
        self._settings.setValue("pso/max_stall", max_stall)

    pso_max_stall: int = Property(int, _get_pso_max_stall, _set_pso_max_stall)

    def _get_pso_max_iter(self) -> int:
        """Returns the maximum PSO iterations."""
        return int(str(self._settings.value("pso/max_iter", 100, type=int)))

    def _set_pso_max_iter(self, max_iter: int) -> None:
        """Sets the maximum PSO iterations."""
        self._logger.debug(f"Setting PSO max_iter to '{max_iter}'")
        self._settings.setValue("pso/max_iter", max_iter)

    pso_max_iter: int = Property(int, _get_pso_max_iter, _set_pso_max_iter)

    def _get_pso_stall_windows_required(self) -> int:
        """Returns the required number of stall windows for PSO convergence."""
        return int(str(self._settings.value("pso/stall_windows_required", 3, type=int)))

    def _set_pso_stall_windows_required(self, stall_windows_required: int) -> None:
        """Sets the required number of stall windows for PSO convergence."""
        self._logger.debug(f"Setting PSO stall_windows_required to '{stall_windows_required}'")
        self._settings.setValue("pso/stall_windows_required", stall_windows_required)

    pso_stall_windows_required: int = Property(int, _get_pso_stall_windows_required, _set_pso_stall_windows_required)

    def _get_pso_space_factor(self) -> float:
        """Returns the PSO search-space factor."""
        return float(str(self._settings.value("pso/space_factor", 0.001, type=float)))

    def _set_pso_space_factor(self, space_factor: float) -> None:
        """Sets the PSO search-space factor."""
        self._logger.debug(f"Setting PSO space_factor to '{space_factor}'")
        self._settings.setValue("pso/space_factor", space_factor)

    pso_space_factor: float = Property(float, _get_pso_space_factor, _set_pso_space_factor)

    def _get_pso_convergence_factor(self) -> float:
        """Returns the PSO convergence factor."""
        return float(str(self._settings.value("pso/convergence_factor", 1e-2, type=float)))

    def _set_pso_convergence_factor(self, convergence_factor: float) -> None:
        """Sets the PSO convergence factor."""
        self._logger.debug(f"Setting PSO convergence_factor to '{convergence_factor}'")
        self._settings.setValue("pso/convergence_factor", convergence_factor)

    pso_convergence_factor: float = Property(float, _get_pso_convergence_factor, _set_pso_convergence_factor)

    def get_pso_hyper_parameters(self) -> PsoHyperparameters:
        """Returns the PSO hyperparameters."""
        return PsoHyperparameters(
            randomness=self.pso_randomness,
            u1=self.pso_u1,
            u2=self.pso_u2,
            initial_range=(self.pso_initial_range_start, self.pso_initial_range_end),
            initial_swarm_span=self.pso_initial_swarm_span,
            min_neighbors_fraction=self.pso_min_neighbors_fraction,
            max_stall=self.pso_max_stall,
            max_iter=self.pso_max_iter,
            stall_windows_required=self.pso_stall_windows_required,
            space_factor=self.pso_space_factor,
            convergence_factor=self.pso_convergence_factor,
        )

    # -------------------
    # QM-File loader
    # -------------------
    def get_qm_file(self, lang_key: str, translator: str | None = None) -> Path:
        """Returns the path to a QM file for the requested translator.

        Args:
            lang_key (str): Language of the QM file (e.g., "en", "de").
            translator (str | None): Translator key (e.g., "app", "report").
                If None, the first configured translator is used.
        """
        translator_key = translator or next(iter(self._translator_cfg.keys()))
        base_name = self._translator_cfg.get(translator_key)
        if not base_name:
            raise KeyError(f"Unknown translator key '{translator_key}'. Valid: {', '.join(self._translator_cfg)}")
        return self._i18n_base_dir / f"{base_name}{lang_key}.qm"

    def get_qm_files(self, lang_key: str) -> dict[str, Path]:
        """Returns paths to all QM files for the requested language."""
        return {
            key: self._i18n_base_dir / f"{base_name}{lang_key}.qm"
            for key, base_name in self._translator_cfg.items()
        }

    def get_translator_keys(self) -> list[str]:
        """Returns configured translator keys (e.g., ['app', 'report'])."""
        return list(self._translator_cfg.keys())

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
        path: Path = Path(path)
        if not path.is_absolute():
            path = self._config_base_dir / path

        if not path.exists():
            self._logger.error(f"JSON file not found: {path}")
            raise FileNotFoundError(f"JSON file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            self._logger.debug(f"Loaded JSON from {path}")
            return json.load(f)

    def _load_language(self) -> tuple[list[str], dict[str, str]]:
        lang_json = self._load_json(self._config_base_dir / "languages.json")
        languages = list(lang_json.get("languages", []))

        translators_cfg = lang_json.get("translators")
        translators: dict[str, str] = {}

        if translators_cfg:
            for prop in translators_cfg.items():
                name, cfg = prop
                if isinstance(cfg, dict):
                    base_name = cfg.get("base_file_name", "")
                else:
                    base_name = str(cfg)
                if not base_name:
                    raise ValueError(f"Translator '{name}' must define a base_file_name")
                translators[name] = base_name
        else:
            # Backward compatibility with older config
            base_file_name = lang_json.get("base_file_name", "app_")
            translators = {"app": base_file_name}

        self._logger.debug(f"Loaded languages from {lang_json}")
        return languages, translators

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

    @staticmethod
    def _get_system_theme() -> str:
        """Maps the current system color scheme to an available app theme."""
        app = QGuiApplication.instance()
        if app is not None and app.styleHints().colorScheme() == Qt.ColorScheme.Light:
            return "light"
        return "dark"

    @Slot()
    def reset_pso_settings(self) -> None:
        """Reset all PSO settings to defaults by removing stored overrides."""

        pso_keys = [
            "pso/swarm_size",
            "pso/repeat_runs",
            "pso/randomness",
            "pso/u1",
            "pso/u2",
            "pso/initial_range_start",
            "pso/initial_range_end",
            "pso/initial_swarm_span",
            "pso/min_neighbors_fraction",
            "pso/max_stall",
            "pso/max_iter",
            "pso/stall_windows_required",
            "pso/space_factor",
            "pso/convergence_factor",
        ]

        for key in pso_keys:
            self._logger.debug(f"Resetting PSO key: {key}")
            self._settings.remove(key)

        self._settings.sync()
