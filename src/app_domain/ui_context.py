from dataclasses import dataclass

from models import SettingsModel
from viewmodels import LanguageViewModel, ThemeViewModel


@dataclass(frozen=True)
class UiContext:
    settings: SettingsModel
    vm_lang: LanguageViewModel
    vm_theme: ThemeViewModel
