from PySide6.QtCore import QObject, QTranslator, QCoreApplication, Slot, Signal, Property
import logging

from models import SettingsModel
from .baseViewModel import BaseViewModel


class LanguageViewModel(BaseViewModel):
    """
    ViewModel responsible for managing application language changes.

    Handles:
    - Loading and installing Qt translation files
    - Persisting selected language via SettingsModel
    - Exposing current language to the View
    """

    languageChanged = Signal()

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        super().__init__(parent)

        self._logger = logging.getLogger(f"ViewModel.{self.__class__.__name__}")

        self._settings = settings
        self._translator = QTranslator()
        self._current_lang: str = ""

        # Cached language configuration (e.g. display names, codes)
        self._lang_cfg = settings.get_languages_cfg()

        # Initialize language from settings
        self.set_language(self._settings.get_language())

    @Slot(str)
    def set_language(self, lang_code: str) -> None:
        """
        Change application language.

        Loads the corresponding .qm file,
        installs translator,
        updates settings,
        and notifies the View.
        """

        if lang_code == self._current_lang:
            self._logger.debug(f"Language '{lang_code}' already active — no change")
            return

        self._logger.debug(f"Changing language from '{self._current_lang}' to '{lang_code}'")

        # Remove old translator
        QCoreApplication.removeTranslator(self._translator)

        # Load new translation file
        qm_path = self._settings.get_qm_file(lang_code)

        if self._translator.load(str(qm_path)):
            QCoreApplication.installTranslator(self._translator)
            self._logger.debug(f"Loaded translator file '{qm_path}'")
        else:
            self._logger.warning(F"Failed to load translator file '{qm_path}'")

        # Update internal state
        self._current_lang = lang_code

        # Persist selection
        self._settings.set_language(lang_code)

        # Notify View
        self.languageChanged.emit()

    def _get_current_language(self) -> str:
        """Return currently active language code."""
        return self._current_lang

    current_language = Property(str, _get_current_language, notify=languageChanged)  # type: ignore[assignment]

    def get_lang_cfg(self) -> dict:
        return self._lang_cfg