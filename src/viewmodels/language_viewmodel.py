from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtCore import QObject, QCoreApplication, QTranslator, Signal, Slot

from utils import LoggedProperty
from .base_viewmodel import BaseViewModel
from app_types import LanguageType

if TYPE_CHECKING:
    from models import SettingsModel


class LanguageViewModel(BaseViewModel):
    """ViewModel that manages app language selection and translation loading."""

    languageChanged = Signal()

    def __init__(self, settings: SettingsModel, parent: QObject = None):
        super().__init__(parent)

        self._settings = settings
        self._translator_keys = self._settings.get_translator_keys()
        self._translators = {key: QTranslator() for key in self._translator_keys}
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

        for translator in self._translators.values():
            QCoreApplication.removeTranslator(translator)

        qm_files = self._settings.get_qm_files(lang_code.value)
        for key in self._translator_keys:
            translator = self._translators.get(key)
            if translator is None:
                continue
            qm_path = qm_files.get(key)
            if qm_path and translator.load(str(qm_path)):
                QCoreApplication.installTranslator(translator)
                self.logger.debug(f"Loaded translator '{key}' file '{qm_path}'")
            else:
                self.logger.warning(f"Failed to load translator '{key}' file '{qm_path}'")

        self._current_lang = lang_code
        self._settings.set_language(lang_code.value)
        self.languageChanged.emit()

    current_language = LoggedProperty(
        path="_current_lang",
        signal="languageChanged",
        typ=LanguageType,
        read_only=True,
    )

