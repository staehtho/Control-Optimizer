from PySide6.QtCore import QObject, QCoreApplication, QTranslator, Signal, Slot

from models import SettingsModel
from utils import LoggedProperty
from .base_viewmodel import BaseViewModel
from .types import LanguageType


class LanguageViewModel(BaseViewModel):
    """ViewModel that manages app language selection and translation loading."""

    languageChanged = Signal()

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        super().__init__(parent)

        self._settings = settings
        self._translator = QTranslator()
        self._current_lang: LanguageType | None = None

        # Initialize language from persisted settings.
        self.set_language(LanguageType(self._settings.get_language()))

    def _connect_signals(self) -> None:
        # No signals to connect
        ...

    @Slot(str)
    def set_language(self, lang_code: LanguageType) -> None:
        """Load and activate the requested language code."""
        if lang_code == self._current_lang:
            self.logger.debug(f"Language '{lang_code}' already active -> no change")
            return

        self.logger.debug(f"Changing language from '{self._current_lang}' to '{lang_code}'")

        QCoreApplication.removeTranslator(self._translator)
        qm_path = self._settings.get_qm_file(lang_code.value)

        if self._translator.load(str(qm_path)):
            QCoreApplication.installTranslator(self._translator)
            self.logger.debug(f"Loaded translator file '{qm_path}'")
        else:
            self.logger.warning(f"Failed to load translator file '{qm_path}'")

        self._current_lang = lang_code
        self._settings.set_language(lang_code.value)
        self.languageChanged.emit()

    current_language = LoggedProperty(
        path="_current_lang",
        signal="languageChanged",
        typ=LanguageType,
        read_only=True,
    )
